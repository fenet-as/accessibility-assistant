from assistant.api.routers import admin, careers, channels, lti, system, tutoring

ALL_ROUTERS = [tutoring.router, careers.router, admin.router, channels.router, lti.router, system.router]
