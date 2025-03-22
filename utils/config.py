"""Configuration settings for the Discord bot."""

# Bot prefix for commands
PREFIX = "!"

# Economy settings
DAILY_REWARD = 100  # Amount given for daily reward
ACTIVITY_BONUS = 10  # Amount given for being active in a company
TIMEOUT_COST = 50    # Cost to timeout someone

# Role IDs (as integers for comparison in code)
PROTECTED_ROLES = [
    1352694494843240448,  # Owner
    1352694494813749308,  # Admin
    1352694494813749307,  # Moderator/staff
]

# Timeout permissions (role_id: seconds)
TIMEOUT_PERMISSIONS = {
    1352694494797234234: 10,    # level 5 - 10 seconds
    1352694494797234235: 30,    # level 10 - 30 seconds
    1352694494797234236: 60,    # level 20 - 60 seconds
    1352694494797234237: 120,   # level 35 - 2 minutes
    1352694494813749299: 300,   # level 50 - 5 minutes
}

# Role name mapping for reference
ROLE_NAMES = {
    1352694494843240448: "Owner",
    1352694494813749308: "Admin",
    1352694494813749307: "Moderator/staff",
    1352694494797234234: "level 5",
    1352694494797234235: "level 10",
    1352694494797234236: "level 20",
    1352694494797234237: "level 35",
    1352694494813749299: "level 50",
}

# Robbery settings
MIN_ROBBERS = 5  # Minimum number of people needed to rob someone
ROBBERY_COOLDOWN = 3600  # Cooldown in seconds (1 hour) before a user can be robbed again

# Quest settings
QUEST_COOLDOWN = 1800  # Cooldown in seconds (30 minutes) between quests
