"""LTI 1.3 (Level 3 integration). The launch handler is a stub until a real platform is registered."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends

from assistant.api.dependencies import get_container
from assistant.container import Container

router = APIRouter(prefix="/api/lti", tags=["LTI 1.3 Standard"])

LESSON_PATH = "/savanna/pages/concept-with-navigation.html"


@router.get("/config.json")
def lti_configuration(container: Container = Depends(get_container)) -> Dict[str, Any]:
    """Tool configuration manifest for Canvas, Moodle or Blackboard."""
    host = container.settings.host_url
    return {
        "title": "ALX Accessibility Assistant & Tutor",
        "description": "Accessible multilingual AI tutor and career gateway module.",
        "oidc_initiation_url": f"{host}/api/lti/login",
        "target_link_uri": f"{host}{LESSON_PATH}",
        "extensions": [
            {
                "platform": "canvas.instructure.com",
                "privacy_level": "anonymous",
                "settings": {
                    "text": "ALX Tutor",
                    "placements": [
                        {"placement": "course_navigation", "message_type": "LtiResourceLinkRequest"}
                    ],
                },
            }
        ],
        "public_jwk_url": f"{host}/api/lti/jwks.json",
    }


@router.post("/launch")
def lti_launch(payload: Optional[Dict[str, Any]] = Body(default=None)) -> Dict[str, Any]:
    """Simulated LTI launch; real deployments must validate the platform's id_token (JWT)."""
    return {
        "status": "authenticated",
        "standard": "LTI-1p3",
        "context": "VA-1: VA Foundations & Professional Identity",
        "redirect_url": LESSON_PATH,
    }
