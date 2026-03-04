"""Email and WhatsApp rendering and delivery for Daily Protocol."""

__all__ = [
    "render_html",
    "render_text",
    "send_email",
    "DeliveryResult",
    "render_whatsapp",
    "send_whatsapp",
]


def __getattr__(name: str) -> object:
    """Lazy import for delivery package public API."""
    if name in ("render_html", "render_text", "build_subject"):
        from biointelligence.delivery.renderer import (
            build_subject,
            render_html,
            render_text,
        )

        _lookup = {
            "render_html": render_html,
            "render_text": render_text,
            "build_subject": build_subject,
        }
        return _lookup[name]
    if name == "send_email":
        from biointelligence.delivery.sender import send_email

        return send_email
    if name == "DeliveryResult":
        from biointelligence.delivery.sender import DeliveryResult

        return DeliveryResult
    if name == "render_whatsapp":
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        return render_whatsapp
    if name == "send_whatsapp":
        from biointelligence.delivery.whatsapp_sender import send_whatsapp

        return send_whatsapp
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
