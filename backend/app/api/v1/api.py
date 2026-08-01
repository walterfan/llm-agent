from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    admin_recommendations,
    auth,
    backup,
    cities,
    coach,
    emails,
    factory,
    knowledge,
    learning,
    llm_settings,
    medical_paper,
    memory,
    philosophy,
    rbac,
    recommendations,
    scheduled,
    secretary,
    translation,
    users,
    weather,
)

api_router = APIRouter()

# Include authentication routes
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Include user management routes
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Include admin routes (user management)
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

# Include admin recommendation routes
api_router.include_router(
    admin_recommendations.router,
    prefix="/admin/recommendations",
    tags=["admin-recommendations"],
)

# Include RBAC routes (role & permission management)
api_router.include_router(rbac.router, prefix="/rbac", tags=["rbac"])

# Include city search routes
api_router.include_router(cities.router, prefix="/cities", tags=["cities"])

# Include weather routes
api_router.include_router(weather.router, prefix="/weather", tags=["weather"])

# Include recommendations routes
api_router.include_router(
    recommendations.router, prefix="/recommendations", tags=["recommendations"]
)

# Include email routes
api_router.include_router(emails.router, prefix="", tags=["emails"])

# Include scheduled job routes (for cronjob)
api_router.include_router(scheduled.router, prefix="/scheduled", tags=["scheduled"])

# Include Personal Secretary routes
api_router.include_router(secretary.router, prefix="/secretary", tags=["secretary"])

# Include Learning routes
api_router.include_router(learning.router, prefix="/learning", tags=["learning"])

# Include Medical Paper Writing Assistant routes
api_router.include_router(
    medical_paper.router, prefix="/medical-paper", tags=["medical-paper"]
)

# Include Translation routes
api_router.include_router(
    translation.router, prefix="/translation", tags=["translation"]
)

# Include Philosophy Master routes
api_router.include_router(
    philosophy.router, prefix="/philosophy", tags=["philosophy-master"]
)

# Include Knowledge base routes (RAG documents, query)
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])

# Include Coach routes (goals, sessions, progress, chat)
api_router.include_router(coach.router, prefix="/coach", tags=["coach"])

# Include Database Backup routes
api_router.include_router(backup.router, prefix="/backup", tags=["backup"])

# Include LLM Settings routes (per-user LLM configuration)
api_router.include_router(
    llm_settings.router, prefix="/llm-settings", tags=["llm-settings"]
)

# Include AI Agent Factory routes (孵化器: compile / approve / publish / run)
api_router.include_router(factory.router, prefix="/factory", tags=["agent-factory"])
api_router.include_router(memory.router, prefix="/memory", tags=["agent-memory"])
