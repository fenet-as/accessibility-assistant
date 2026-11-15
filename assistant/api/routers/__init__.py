from assistant.api.routers import (
    admin,
    careers,
    channels,
    conversations,
    lti,
    offline,
    speech,
    system,
    tutoring,
)

ALL_ROUTERS = [
    tutoring.router,
    careers.router,
    admin.router,
    channels.router,
    lti.router,
    offline.router,
    speech.router,
    system.router,
    conversations.router,
]
