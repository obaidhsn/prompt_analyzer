"""The ``@track`` decorator — the entire public capture API.

Design guarantees:

* **Never crashes the caller.** All PromptAnalyzer logic is wrapped so that an
  internal error is logged and swallowed; the user's function result (or its
  exception) is always propagated faithfully.
* **Sub-millisecond overhead.** The only synchronous work is timing plus
  adapter extraction; persistence is handed to a background thread.
* **Sync and async.** Coroutine functions are wrapped with an async wrapper.
"""

from __future__ import annotations

import functools
import inspect
import time
from collections.abc import Callable
from typing import Any, TypeVar

from .adapters import Adapter, GenericAdapter, detect_adapter, get_adapter
from .config import get_config
from .instrument import CallCapture, capture_context, install_all
from .logging_utils import debug
from .normalize import NormalizedRecord
from .pricing import estimate_cost
from .storage import RunPayload, enqueue_run

__all__ = ["track"]

F = TypeVar("F", bound=Callable[..., Any])

_MAX_FIELD_CHARS = 100_000  # guardrail against pathologically large payloads


def track(
    name: str | None = None,
    *,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    provider: str | None = None,
    project: str | None = None,
    system: Callable[[tuple[Any, ...], dict[str, Any]], Any] | None = None,
    user: Callable[[tuple[Any, ...], dict[str, Any]], Any] | None = None,
    response: Callable[[Any], Any] | None = None,
    model: Callable[[tuple[Any, ...], dict[str, Any], Any], Any] | None = None,
) -> Callable[[F], F]:
    """Decorate an LLM-calling function to capture prompts, responses and metrics.

    Parameters
    ----------
    name:
        Project name this function's runs are grouped under. Falls back to the
        ``PROMPTANALYZER_PROJECT`` environment variable, then ``"default"``.
    tags, metadata:
        Free-form labels and structured metadata stored with every run.
    provider:
        Force a specific adapter (e.g. ``"anthropic"``). When omitted the adapter
        is auto-detected from the return value.
    project:
        Explicit project name; takes precedence over ``name``.
    system, user, response, model:
        Optional extractor callables enabling the generic adapter for custom
        libraries. Any provided extractor activates the generic adapter.
    """

    custom_extractors = any(x is not None for x in (system, user, response, model))

    def decorator(func: F) -> F:
        resolved_name = project or name
        try:
            signature = inspect.signature(func)
        except (TypeError, ValueError):  # builtins / C functions
            signature = None

        def _resolve_adapter(args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> Adapter:
            if custom_extractors:
                return GenericAdapter(
                    provider=provider,
                    system=system,
                    user=user,
                    response=response,
                    model=model,
                )
            if provider:
                chosen = get_adapter(provider)
                if chosen is not None:
                    return chosen
            return detect_adapter(args, kwargs, result)

        def _bound_kwargs(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
            """Expose positional arguments by name so extractors can find them."""
            if signature is None:
                return kwargs
            try:
                bound = signature.bind_partial(*args, **kwargs)
                return dict(bound.arguments)
            except TypeError:
                return kwargs

        def _effective_inputs(
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
            result: Any,
            capture: CallCapture | None,
        ) -> tuple[tuple[Any, ...], dict[str, Any], Any, str | None]:
            """Pick the best source of truth: an intercepted client call, else args.

            Custom extractors always operate on the decorated function itself.
            Otherwise, if the client was auto-instrumented and recorded a real
            request/response, use that — it carries the messages, model and usage
            even when the function returns just the answer text.
            """
            if not custom_extractors and capture is not None and capture.last is not None:
                call = capture.last
                return (), dict(call.request), call.result, call.provider
            return args, _bound_kwargs(args, kwargs), result, None

        def _build_payload(
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
            result: Any,
            latency_ms: float,
            error: BaseException | None,
            capture: CallCapture | None,
        ) -> RunPayload:
            cfg = get_config()
            eff_args, eff_kwargs, eff_result, provider_hint = _effective_inputs(
                args, kwargs, result, capture
            )
            record = NormalizedRecord()
            try:
                if provider_hint and not provider and not custom_extractors:
                    adapter = get_adapter(provider_hint) or _resolve_adapter(
                        eff_args, eff_kwargs, eff_result
                    )
                else:
                    adapter = _resolve_adapter(eff_args, eff_kwargs, eff_result)
                call_rec = adapter.from_call(eff_args, eff_kwargs)
                record.merge(call_rec)
                if eff_result is not None:
                    resp_rec = adapter.from_response(eff_result)
                    record.merge(resp_rec)
            except Exception as exc:  # extraction must never break tracking
                debug("adapter extraction failed: %s", exc)
            record.finalize()

            if record.cost is None and cfg.log_cost:
                record.cost = estimate_cost(record.model, record.input_tokens, record.output_tokens)

            return RunPayload(
                project=(resolved_name or cfg.project),
                function_name=getattr(func, "__name__", None),
                provider=record.provider,
                model=record.model,
                system_prompt=_clip(record.system_prompt),
                user_input=_clip(record.user_prompt),
                response=_clip(record.response),
                latency_ms=round(latency_ms, 3),
                input_tokens=record.input_tokens,
                output_tokens=record.output_tokens,
                total_tokens=record.total_tokens,
                cost=record.cost,
                tags=tags,
                metadata={**(metadata or {}), **record.metadata} or None,
                error=_format_error(error),
                env=cfg.env,
            )

        def _log(
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
            result: Any,
            start: float,
            error: BaseException | None,
            capture: CallCapture | None,
        ) -> None:
            if not get_config().enabled:
                return
            try:
                latency_ms = (time.perf_counter() - start) * 1000.0
                payload = _build_payload(args, kwargs, result, latency_ms, error, capture)
                enqueue_run(payload)
            except Exception as exc:  # final safety net
                debug("tracking failed: %s", exc)

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                install_all()
                start = time.perf_counter()
                error: BaseException | None = None
                result: Any = None
                with capture_context() as capture:
                    try:
                        result = await func(*args, **kwargs)
                        return result
                    except BaseException as exc:  # noqa: BLE001 — re-raised below
                        error = exc
                        raise
                    finally:
                        _log(args, kwargs, result, start, error, capture)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            install_all()
            start = time.perf_counter()
            error: BaseException | None = None
            result: Any = None
            with capture_context() as capture:
                try:
                    result = func(*args, **kwargs)
                    return result
                except BaseException as exc:  # noqa: BLE001 — re-raised below
                    error = exc
                    raise
                finally:
                    _log(args, kwargs, result, start, error, capture)

        return sync_wrapper  # type: ignore[return-value]

    return decorator


def _clip(text: str | None) -> str | None:
    if text is None:
        return None
    if not isinstance(text, str):
        text = str(text)
    if len(text) > _MAX_FIELD_CHARS:
        return text[:_MAX_FIELD_CHARS] + "…[truncated]"
    return text


def _format_error(error: BaseException | None) -> str | None:
    if error is None:
        return None
    return f"{type(error).__name__}: {error}"
