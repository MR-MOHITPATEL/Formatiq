"""
Auto-generates search keywords for each format point in the Health/Nutrition niche.
"""

DEFAULT_KEYWORDS: dict[int, list[str]] = {
    1: [
        "keto vs paleo diet health",
        "intermittent fasting vs calorie restriction",
        "plant based vs carnivore diet",
        "whey protein vs plant protein comparison",
        "green tea vs black coffee benefits",
    ],
    2: [
        "weight loss transformation journey",
        "diabetes reversal success story",
        "from obese to healthy transformation",
        "gut health recovery story",
        "thyroid healing journey",
    ],
    3: [
        "health facts you didn't know",
        "nutrition facts that will shock you",
        "did you know about this vitamin",
        "surprising facts about gut health",
        "hidden facts about sugar health",
    ],
    4: [
        "tips for weight loss naturally",
        "nutrition tips for better health",
        "morning health tips routine",
        "tips to reduce blood sugar",
        "health tips for women over 40",
    ],
    5: [
        "do you always feel tired health",
        "is this happening to your body",
        "signs your gut health is bad",
        "do you have these deficiency symptoms",
        "does this happen to you after eating",
    ],
    6: [
        "health myths debunked nutrition",
        "you are wrong about eating fat",
        "myths about protein health",
        "common diet mistakes you're making",
        "you're drinking water wrong health",
    ],
    7: [
        "patient story diabetes reversal",
        "real case study weight loss",
        "my patient reversed thyroid naturally",
        "case study gut healing",
        "patient with PCOS healed naturally",
    ],
    8: [
        "secret health drink recipe",
        "morning detox concoction benefits",
        "secret remedy ancient recipe",
        "home remedy mixture health benefits",
        "magical health drink ingredients",
    ],
    9: [
        "daily habits causing inflammation",
        "habits that destroy gut health",
        "symptoms of vitamin deficiency",
        "silent killer habits health",
        "bad habits affecting your liver",
    ],
    10: [
        "seed oils are killing you",
        "sugar is destroying your health",
        "processed food ingredient dangers",
        "toxic food ingredient to avoid",
        "why refined flour is dangerous",
    ],
    11: [
        "turmeric health benefits science",
        "ginger health benefits research",
        "ashwagandha benefits evidence",
        "moringa health benefits nutrition",
        "amla benefits for health",
    ],
    12: [
        "DIY weight loss plan at home",
        "how to reverse diabetes at home",
        "DIY gut healing protocol",
        "homemade health plan for thyroid",
        "DIY detox plan 7 days",
    ],
    13: [
        "trending health topic solution",
        "current nutrition news what to do",
        "new research diabetes what to eat",
        "latest gut health study recommendations",
        "health news 2024 what it means for you",
    ],
    14: [
        "best supplements ranked health",
        "protein powder rating comparison",
        "vitamin D supplement rating",
        "rating cooking oils healthiest",
        "best probiotic brands rated",
    ],
    15: [
        "health dos and don'ts",
        "diet tips do this not that",
        "morning routine dos and don'ts health",
        "gut health dos and don'ts",
        "weight loss do this not that",
    ],
    16: [
        "how to make healthy meal prep",
        "how to detox your body DIY",
        "how to fix gut health naturally",
        "how to reduce inflammation at home",
        "how to make fermented foods at home",
    ],
    17: [
        "best protein powder review",
        "health supplement honest review",
        "probiotic brand review nutrition",
        "best multivitamin review honest",
        "nutrition bar review honest",
    ],
    18: [
        "magnesium supplement benefits",
        "omega 3 supplement why you need it",
        "vitamin D3 K2 supplement benefits",
        "creatine health benefits not just gym",
        "berberine supplement benefits blood sugar",
    ],
    19: [
        "do you have insulin resistance signs",
        "how to know if you have leaky gut",
        "thyroid problem signs diagnosis",
        "signs of chronic inflammation body",
        "how to test gut health at home",
    ],
    20: [
        "CGM continuous glucose monitor results",
        "what my blood sugar does after eating",
        "glucose spikes what to do CGM",
        "continuous glucose monitor diet experiment",
        "blood sugar test real food CGM",
    ],
    21: [
        "podcast clip nutrition expert",
        "interview health doctor short clip",
        "best podcast moments nutrition",
        "Joe Rogan health clip nutrition",
        "expert interview gut health clip",
    ],
    22: [
        "how I reversed my diabetes",
        "PCOS reversal story natural",
        "how I healed my gut health",
        "fatty liver reversal natural",
        "how to reverse insulin resistance naturally",
    ],
    23: [
        "reacting to viral health video",
        "nutrition expert reacts to trends",
        "doctor reacts to diet advice",
        "reacting to food influencer health claims",
        "nutritionist reacts to popular diet",
    ],
    24: [
        "contact me for health consultation",
        "DM me your health questions",
        "comment your health problem below",
        "join my health program link in bio",
        "free health consultation how to get",
    ],
}


def get_keywords_for_format(format_point_number: int, custom_keywords: list[str] | None = None) -> list[str]:
    """Return keywords for a format point, merging custom overrides."""
    base = DEFAULT_KEYWORDS.get(format_point_number, [])
    if custom_keywords:
        # Custom keywords first, then fill up with defaults
        combined = custom_keywords + [k for k in base if k not in custom_keywords]
        return combined[:8]
    return base
