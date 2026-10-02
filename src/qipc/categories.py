"""The 8 fixed issue categories this station's public-affairs show tracks.

Real stations choose their own categories each quarter based on what the
show actually covered; this project fixes 8 up front so the synthetic
segment log and the ranking report have a stable, named set to work with.
"""

CATEGORIES = (
    "Education",
    "Housing",
    "Public Safety",
    "Health",
    "Environment",
    "Transportation",
    "Economic Development",
    "Civic Engagement",
)

assert len(CATEGORIES) == 8
assert len(set(CATEGORIES)) == 8
