from assistant.api.routers import admin, careers, channels, lti, offline, system, tutoring, voice

ALL_ROUTERS = [
    tutoring.router, careers.router, admin.router, channels.router,
    lti.router, offline.router, system.router, voice.router,
]
