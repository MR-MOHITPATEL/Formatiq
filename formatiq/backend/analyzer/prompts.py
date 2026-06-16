"""
All Claude prompts for FormatIQ analysis.
"""

FORMAT_POINTS_LIST = """
1. A vs B (comparison style)
2. Underdog to Hero (transformation narrative)
3. DYK - Fact (Did You Know, fact-based)
4. Tips (listicle / tips format)
5. Is this You / Does it happen to you? (relatable problem opener)
6. If you think so, You are wrong (myth-busting / counter-intuitive)
7. Patient problem opener (specific case study as hook)
8. Concoction / Secret Mix (secret recipe or mix with benefits)
9. DYK Villain - habit/symptom (bad habits or symptoms as villain)
10. Villain based (ingredient or intent as villain)
11. Natural Ingredient centric (food/natural ingredient spotlight)
12. DIY - Goal based (do-it-yourself goal-oriented tutorial)
13. Current Affair + DIY (trending news + DIY recommendation)
14. Ingredient/Compound rating (rating system with rationale)
15. IG Reels type - Tips/DOs DONTs (short-form style content)
16. How to? with DIY (how-to tutorial with hands-on component)
17. Product ratings (product review including branded)
18. Supplement Recommendations (chemical/synthetic supplement benefits)
19. Diagnosis (diagnostic/assessment style)
20. CGM Format (continuous glucose monitor data-driven)
21. Podcast split videos (long-form podcast excerpt style)
22. Reversal (reversal/recovery story)
23. Reaction Videos (creator reacts to content/trends/studies)
24. Invite to contact (CTA-heavy, inviting viewer engagement)
"""


def build_video_analysis_prompt(
    title: str,
    description: str,
    transcript: str | None,
    channel_name: str,
    view_count: int,
) -> str:
    content_section = f"""
VIDEO TITLE: {title}
CHANNEL: {channel_name}
VIEWS: {view_count:,}

DESCRIPTION:
{description[:1500] if description else 'Not available'}
"""

    if transcript:
        content_section += f"""
TRANSCRIPT (first 12000 chars):
{transcript[:12000]}
"""
    else:
        content_section += "\nTRANSCRIPT: Not available — analyze title and description only.\n"

    return f"""You are an expert YouTube content strategist specializing in Health, Nutrition, and Wellness content analysis.

Analyze this YouTube video and return a JSON response with EXACTLY the structure shown below.

{content_section}

FORMAT POINTS TO SCORE (0-10):
{FORMAT_POINTS_LIST}

SCORING GUIDE:
- 0 = Not used at all
- 1-3 = Barely present / weak execution
- 4-6 = Moderate presence / average execution
- 7-9 = Strong presence / good execution
- 10 = Exceptional, textbook example of this format

Return ONLY valid JSON (no markdown, no explanation) with this exact structure:
{{
  "concept_summary": "2-3 sentence summary of the core concept being explained",
  "script_analysis": "How is the script structured? What hooks, transitions, CTAs are used? 3-4 sentences.",
  "format_point_scores": {{
    "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0,
    "7": 0, "8": 0, "9": 0, "10": 0, "11": 0, "12": 0,
    "13": 0, "14": 0, "15": 0, "16": 0, "17": 0, "18": 0,
    "19": 0, "20": 0, "21": 0, "22": 0, "23": 0, "24": 0
  }},
  "format_point_flags": {{
    "1": false, "2": false, "3": false, "4": false, "5": false, "6": false,
    "7": false, "8": false, "9": false, "10": false, "11": false, "12": false,
    "13": false, "14": false, "15": false, "16": false, "17": false, "18": false,
    "19": false, "20": false, "21": false, "22": false, "23": false, "24": false
  }},
  "best_moments": [
    {{"timestamp": "MM:SS or description", "excerpt": "quote or description", "note": "why this works"}}
  ],
  "what_works": ["point 1", "point 2", "point 3"],
  "what_doesnt_work": ["weakness 1", "weakness 2"],
  "health_niche_angle": "Specific health topic and angle covered (e.g., Type 2 Diabetes reversal through intermittent fasting)"
}}

Set format_point_flags to true for any format_point_scores >= 4.
Include 3-5 best_moments objects.
"""


def build_format_point_report_prompt(
    format_point_name: str,
    format_point_number: int,
    top_videos_summary: str,
    avg_scores: dict,
) -> str:
    return f"""You are a YouTube content strategist for Health/Nutrition/Wellness content.

Based on this data about Format Point #{format_point_number}: "{format_point_name}", generate a strategic report.

TOP PERFORMING VIDEOS DATA:
{top_videos_summary}

AVERAGE SCORES ACROSS ALL 24 FORMAT POINTS (for videos in this category):
{avg_scores}

Generate a JSON report with this structure:
{{
  "what_works_in_this_niche": "2-3 sentences on what topics and angles work best for this format in Health/Nutrition",
  "recommended_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "script_structure_template": {{
    "hook": "Description of optimal hook for this format (1-2 sentences)",
    "intro": "What to cover in first 60 seconds",
    "body": "Main content structure and key sections",
    "cta": "Optimal call to action for this format"
  }},
  "content_angles": ["angle1", "angle2", "angle3"],
  "avoid": ["mistake1", "mistake2"]
}}

Return ONLY valid JSON.
"""


def build_angle_analysis_prompt(
    title: str,
    description: str,
    transcript: str | None,
    channel_name: str,
    view_count: int,
    is_short: bool = False,
) -> str:
    content = f"""VIDEO TITLE: {title}
CHANNEL: {channel_name}
VIEWS: {view_count:,}

DESCRIPTION:
{description or 'Not available'}
"""
    if transcript:
        content += f"""
FULL TRANSCRIPT:
{transcript}
"""
    else:
        content += "\nTRANSCRIPT: Not available — analyze title and description only.\n"

    short_note = """
NOTE: This is a SHORT-FORM video (under 2:30 minutes). Adjust your expectations accordingly:
- A Short can only realistically have 1-3 strong angles in 60-150 seconds
- Do NOT mark angles as "missing" just because there wasn't time for them
- Focus on Villain and Virality as the primary angles for Shorts
- overall_strength should reflect how well the angles that ARE present are executed, not penalize for missing ones
""" if is_short else ""

    return f"""You are a YouTube content strategy expert analyzing health/medical videos for a doctor-creator.
{short_note}
Analyze this video across exactly 5 storytelling angles. For each angle:
- Determine if it is PRESENT or MISSING in the video
- Write a short description of HOW it is used (or why it is missing)
- Extract 2-3 EXACT lines/moments from the transcript or title that represent this angle (or leave empty if absent)

Here are the 5 angles and their definitions:

1. VILLAIN — The thing the audience should be angry at or worried about. Not always a person. Could be food adulteration, misinformation, ultra-processed foods, bad health advice, or a systemic problem. Without a villain, it's just information. With a villain, there's a reason to keep watching.

2. HERO — What helps the audience defeat the villain. Could be a food, habit, blood test, mindset, framework, or simply correct information. The hero should leave the audience feeling MORE POWERFUL than before watching.

3. VIRALITY — The moment that makes people stop and think "Wait... what?" Usually comes from a surprising fact, a broken assumption, or a hidden truth. Something people would share with someone else because it challenges what they already believe.

4. CREDIBILITY — What makes people trust this as a doctor, not just an influencer. Numbers, mechanisms, studies, balance. Being willing to say "this person is partly right, but here's the missing context." Audience should feel the doctor follows evidence, not opinion.

5. MORAL GROUND — The reason the audience supports the doctor. Not scoring points or winning arguments — but protecting viewers from bad information. "Millions of people could make health decisions based on this claim, so let's look at the evidence."

{content}

Return ONLY valid JSON (no markdown, no explanation) with this exact structure:
{{
  "villain": {{
    "present": true,
    "description": "What is the villain in this video and how is it framed?",
    "exact_lines": ["exact quote or moment 1", "exact quote or moment 2"]
  }},
  "hero": {{
    "present": true,
    "description": "What is the hero and how does it empower the viewer?",
    "exact_lines": ["exact quote or moment 1", "exact quote or moment 2"]
  }},
  "virality": {{
    "present": false,
    "description": "Is there a 'wait... what?' moment? What is it or what's missing?",
    "exact_lines": []
  }},
  "credibility": {{
    "present": true,
    "description": "What credibility signals are used? Numbers, studies, balance?",
    "exact_lines": ["exact quote showing data or nuance"]
  }},
  "moral_ground": {{
    "present": true,
    "description": "Does the creator feel like they're protecting the viewer or scoring points?",
    "exact_lines": ["exact quote showing care for the audience"]
  }},
  "format_point_mapping": {{
    "6": "Myth-busting angle maps to 'If you think so, You are wrong' format point",
    "9": "Villain framing of bad habits maps to DYK Villain format"
  }},
  "overall_strength": 7,
  "script_inspiration": "One sentence: what is the single most powerful idea a creator could take from this video to build their own script around?"
}}

Set overall_strength from 1-10 based on how well all 5 angles are used together.
format_point_mapping should reference 2-4 of the 24 format point numbers that best match this video's angles.
"""


def _build_language_block(language: str, channel_style: dict | None = None) -> str:
    """Build language instructions for the script prompt."""
    lang_pattern = (channel_style or {}).get("language_pattern", {})
    auto_mixing = lang_pattern.get("mixing_style", "")
    auto_sample = lang_pattern.get("sample_sentence", "")
    hindi_words = (channel_style or {}).get("vocabulary", {}).get("hindi_words_used", [])

    if language == "english":
        return "\nLANGUAGE: Write entirely in clear, simple English. No Hindi words."

    elif language == "hindi":
        return """\nLANGUAGE: Write entirely in Hindi using Roman script (English alphabet transliteration).
- Medical and scientific terms stay in English (e.g. blood sugar, insulin)
- All Hindi words written in Roman script (e.g. 'aapka swasthya', 'sehat ke liye', 'yeh bahut zaroori hai')
- Do NOT use Devanagari script
- Keep sentences short and conversational"""

    else:  # hinglish (default)
        lines = ["\nLANGUAGE: Write in Hinglish — a natural 50-50 mix of Hindi and English, ALL in Roman script (English alphabet)."]
        lines.append("HINGLISH RULES:")
        lines.append("- Switch between Hindi and English naturally mid-sentence, the way educated Indians speak")
        lines.append("- Hindi words MUST be written in Roman/English script (e.g. 'aaj hum baat karenge', 'yaar', 'dekho', 'samjhe?')")
        lines.append("- Do NOT use Devanagari script at all — every word must be readable in English alphabet")
        lines.append("- Medical/scientific terms always stay in English (insulin, blood sugar, inflammation, etc.)")
        lines.append("- Emotional, relatable words lean Hindi in Roman: yaar, dekho, suno, bilkul, sach mein, matlab, toh")

        if auto_mixing:
            lines.append(f"- This creator's detected pattern: {auto_mixing}")
        if hindi_words:
            lines.append(f"- Their natural Hindi words/phrases: {', '.join(hindi_words[:8])}")
        if auto_sample:
            lines.append(f"- Example sentence in their style: \"{auto_sample}\"")

        return "\n".join(lines)


def _build_style_block(channel_style: dict | None, format_type: str = "longform") -> str:
    """Convert a stored channel style profile into prompt instructions."""
    if not channel_style:
        return ""

    lines = ["\nCREATOR STYLE GUIDE — match this creator's voice exactly:"]

    # For Shorts, inject the shorts-specific style on top
    if format_type == "shorts":
        ss = channel_style.get("shorts_style", {})
        if ss:
            if ss.get("hook_style"):
                lines.append(f"SHORTS HOOK STYLE: {ss['hook_style']}")
            if ss.get("sample_hook"):
                lines.append(f"EXAMPLE HOOK: \"{ss['sample_hook']}\"")
            if ss.get("cta_pattern"):
                lines.append(f"SHORTS CTA: {ss['cta_pattern']}")
            if ss.get("pacing"):
                lines.append(f"PACING: {ss['pacing']}")
            if ss.get("top_topics"):
                lines.append(f"TOP SHORTS TOPICS: {', '.join(ss['top_topics'][:4])}")

    if channel_style.get("tone_description"):
        lines.append(f"TONE: {channel_style['tone_description']}")

    vocab = channel_style.get("vocabulary", {})
    if isinstance(vocab, dict):
        if vocab.get("common_phrases"):
            lines.append(f"THEIR PHRASES: {', '.join(vocab['common_phrases'][:5])}")
        if vocab.get("words_they_avoid"):
            lines.append(f"AVOID THESE WORDS: {', '.join(vocab['words_they_avoid'])}")
        if vocab.get("signature_expressions"):
            lines.append(f"SIGNATURE EXPRESSIONS: {', '.join(vocab['signature_expressions'])}")

    struct = channel_style.get("script_structure", {})
    if isinstance(struct, dict):
        if struct.get("hook_style"):
            lines.append(f"HOOK STYLE: {struct['hook_style']}")
        if struct.get("cta_style"):
            lines.append(f"CTA STYLE: {struct['cta_style']}")

    if channel_style.get("credibility_style"):
        lines.append(f"CREDIBILITY: {channel_style['credibility_style']}")

    if channel_style.get("disclaimer_style"):
        lines.append(f"DISCLAIMER: {channel_style['disclaimer_style']}")

    if channel_style.get("what_makes_them_unique"):
        lines.append(f"UNIQUE VOICE: {channel_style['what_makes_them_unique']}")

    lines.append("IMPORTANT: Write ONLY what is factually supported. No assumptions. No invented statistics. If citing a study or organization, mark it as [CITE: topic] so citations can be added.")
    lines.append(
        "BANNED WORDS — never use these in the script: "
        "'villain', 'hero', 'virality', 'viral moment', 'credibility', 'moral ground', 'scientifically'. "
        "Use natural alternatives instead: "
        "villain → 'asli problem', 'hidden cause', 'real culprit'; "
        "hero → 'solution', 'fix', 'what actually helps'; "
        "credibility → 'research shows', 'studies confirm', 'doctors found'; "
        "scientifically → 'research shows', 'studies show', 'data shows'; "
        "moral ground → skip entirely or rephrase as 'protecting your health'."
    )

    return "\n".join(lines)


def build_shorts_script_prompt(
    topic: str,
    angle: str,
    niche: str,
    evidence_titles: list[str],
    channel_style: dict | None = None,
    language: str = "hinglish",
    competitor_intel: str = "",
) -> str:
    evidence_block = competitor_intel if competitor_intel else (
        "\n".join(f"- {t}" for t in evidence_titles[:5]) if evidence_titles else "No competitor data available — use general best practices."
    )
    style_block = _build_style_block(channel_style, format_type="shorts")
    language_block = _build_language_block(language, channel_style)

    title_instruction = (
        "bilingual title mixing Hindi and English (e.g. 'Sugar का Dangerous Secret | Why You're Always Tired')"
        if language == "hinglish" else
        "title in Hindi Devanagari with English medical terms allowed"
        if language == "hindi" else
        "clear English title, SEO-friendly"
    )

    return f"""You are an expert scriptwriter for doctor/pharmaceutical health content on YouTube Shorts and Instagram Reels.

TOPIC: {topic}
ANGLE: {angle or "General educational angle"}
NICHE: {niche}
{language_block}

COMPETITOR DATA:
{evidence_block}
{style_block}

Write a SHORT-FORM script (MINIMUM 130 words, MAXIMUM 170 words, 60-90 seconds when spoken aloud).
COUNT YOUR WORDS. Do NOT stop before 130 words. The full_script field must contain 130-170 words.

STRUCTURE (must hit all 4 sections):
1. HOOK (5 sec) — Scroll-stopping opening. One sharp line. Make the viewer freeze.
2. PROBLEM (10 sec) — Make them feel the pain of this problem in their own life.
3. INSIGHT (30 sec) — The surprising truth. Use competitor gaps to differentiate. [CITE] any facts.
4. CLOSING (10 sec) — MANDATORY STRUCTURE:
   - Write 1-2 lines that are SPECIFIC to this topic: an emotional reflection, a shareable insight, or an action the viewer should take RIGHT NOW because of what they just learned. Make it feel personal and urgent — NOT generic advice.
   - Then end with EXACTLY this tagline on its own line: "Knowledge is Prevention. Stay connected, stay healthy."
   - DO NOT use: "Thanks & Regards", "follow and subscribe all our channels", "Don't trust blindly", or any other generic sign-off.

WRITING STYLE RULES — follow all of these:
- Write like a real doctor talking to a friend, not reading a textbook
- Use everyday language — no medical jargon unless immediately explained
- Build curiosity: every sentence should make the viewer want to hear the next one
- Feel warm, trustworthy, and human — not corporate or robotic
- Short punchy sentences. No paragraph walls.
- ONLY include claims that are factually accurate — no invented stats or assumptions
- Mark any claim needing a citation as [CITE: brief topic description]
- BANNED WORDS — never write these in the script: 'villain', 'hero', 'virality', 'viral moment', 'credibility', 'moral ground', 'scientifically'. Use instead: asli problem / hidden cause / real culprit (for villain); solution / fix / what actually helps (for hero); research shows / studies confirm / doctors found (for credibility/scientifically).

Return ONLY valid JSON with exactly this structure:
{{
  "full_script": "The complete word-for-word spoken script in the specified language. Use [PAUSE] for natural breath pauses. Use *emphasis* for words to stress. Use [CITE: topic] where a citation is needed.",
  "outline": {{
    "hook": "First 5 seconds — the scroll-stopping opening line",
    "problem": "10 seconds — relatable problem statement",
    "insight": "30 seconds — the core insight or solution",
    "cta": "10 seconds — call to action"
  }},
  "suggested_title": "Exact YouTube Shorts / Reel title — {title_instruction}",
  "hook_line": "The single opening sentence (must be under 10 words, maximum curiosity)",
  "cite_topics": ["topic needing citation 1", "topic needing citation 2"]
}}"""


def build_longform_script_prompt(
    topic: str,
    angle: str,
    niche: str,
    evidence_titles: list[str],
    target_words: int = 2000,
    channel_style: dict | None = None,
    language: str = "hinglish",
    competitor_intel: str = "",
) -> str:
    evidence_block = competitor_intel if competitor_intel else (
        "\n".join(f"- {t}" for t in evidence_titles[:5]) if evidence_titles else "No competitor data available — use general best practices."
    )
    style_block = _build_style_block(channel_style)
    language_block = _build_language_block(language, channel_style)

    title_instruction = (
        "bilingual title mixing Hindi and English (e.g. 'Sugar का Dangerous Secret | Why You're Always Tired')"
        if language == "hinglish" else
        "title in Hindi Devanagari with English medical terms allowed"
        if language == "hindi" else
        "clear English title, curiosity-driven, SEO-friendly"
    )

    return f"""You are an expert scriptwriter for doctor/pharmaceutical health content on YouTube (long-form videos).

TOPIC: {topic}
ANGLE: {angle or "General educational angle"}
NICHE: {niche}
TARGET LENGTH: MINIMUM {target_words} words (approximately 8-12 minutes spoken at 150 words/minute)
{language_block}

COMPETITOR DATA:
{evidence_block}
{style_block}

⚠️ WORD COUNT IS MANDATORY: The full_script field MUST contain at least {target_words} words.
Count sections as you write: Hook (~200w) + Intro (~200w) + Root Cause (~400w) + Prevention (~400w) + Solution (~400w) + Close (~200w) + Closing (~100w) = ~1900 words minimum.
Do NOT summarize or cut short. Write every section in FULL. Do NOT stop until you reach {target_words} words.

Write a LONG-FORM YouTube script covering: root cause of the problem, prevention methods, and actionable solutions.
Use the COMPETITOR DATA above to: (1) match hooks that work for this topic, (2) fill the gaps competitors missed, (3) reference their villain/angle framing as inspiration — but write your own unique version.

WRITING STYLE RULES — follow all of these:
- Open with a story, shocking statistic, or provocative question — NOT "Hi, welcome to my channel"
- Write like a knowledgeable friend explaining this at dinner, not a medical lecture
- Use everyday language — explain any technical term the moment you use it
- Build retention: end each section with a teaser for the next ("लेकिन यहाँ असली बात है...")
- Vary sentence length — mix short punchy lines with longer explanations
- Feel warm, trustworthy, emotionally relatable — never cold or corporate
- ONLY include claims that are factually accurate — no invented stats, no assumptions
- Mark any claim needing a citation as [CITE: brief topic description]
- BANNED WORDS — never write these in the script: 'villain', 'hero', 'virality', 'viral moment', 'credibility', 'moral ground', 'scientifically'. Use instead: asli problem / hidden cause / real culprit (for villain); solution / fix / what actually helps (for hero); research shows / studies confirm / doctors found (for credibility/scientifically).
- CLOSING — MANDATORY STRUCTURE: After the main content, write 2-3 lines that are SPECIFIC to this topic — a shareable insight, an emotional reflection, or a direct action the viewer should take because of what they just learned (e.g. "Isko save karo — aur ghar mein jiski sabse zyada chinta hai tumhe — unhe abhi bhejo"). Then end with EXACTLY this tagline on its own line: "Knowledge is Prevention. Stay connected, stay healthy." DO NOT use generic sign-offs like "Thanks & Regards", "follow and subscribe all our channels", or "Explained in Simple language by a Professional Doctor."

Return ONLY valid JSON with exactly this structure:
{{
  "full_script": "The complete word-for-word spoken script in the specified language. Use [PAUSE] for natural breath pauses. Use *emphasis* for key phrases. Mark section transitions with [SECTION: name]. Use [CITE: topic] where a citation is needed.",
  "outline": {{
    "hook": "Opening 30 seconds — story/stat/question that stops the viewer",
    "intro": "First 60 seconds — why this topic matters to the viewer right now",
    "root_cause": "Main section — what actually causes this problem (surprising facts)",
    "prevention": "Prevention methods with actionable steps",
    "solution": "Practical solutions and what the viewer can do starting today",
    "emotional_close": "Empathetic closing that validates the viewer's struggle",
    "cta": "Topic-specific share/save prompt + 'Knowledge is Prevention. Stay connected, stay healthy.'"
  }},
  "suggested_title": "Exact YouTube video title — {title_instruction}",
  "thumbnail_text": "3-5 words for the thumbnail overlay",
  "hook_line": "The single opening sentence (maximum curiosity and emotional pull)",
  "cite_topics": ["topic needing citation 1", "topic needing citation 2", "topic 3"]
}}"""


def build_next_video_prompt(
    top_format_points: list[dict],
    trending_topics: list[str],
    niche: str,
) -> str:
    fp_summary = "\n".join(
        [f"- Format #{fp['number']}: {fp['name']} (avg views: {fp['avg_views']:,.0f}, top score: {fp['top_score']:.1f}/10)"
         for fp in top_format_points]
    )

    return f"""You are a top YouTube content strategist for {niche}.

Based on performance data, these format points have the highest potential:
{fp_summary}

Trending topics found in analyzed videos:
{chr(10).join(f"- {t}" for t in trending_topics[:15])}

Generate 3 specific video recommendations. Return ONLY valid JSON:
{{
  "recommendations": [
    {{
      "format_point_number": 1,
      "format_point_name": "A vs B",
      "performance_rationale": "Why this format has potential right now",
      "suggested_title": "Exact video title to use",
      "hook": "Opening 15-30 seconds script",
      "script_outline": {{
        "intro": "First 60 seconds outline",
        "body_sections": ["Section 1 topic", "Section 2 topic", "Section 3 topic"],
        "cta": "Closing call to action"
      }},
      "health_topic": "Specific health topic to cover",
      "estimated_view_potential": "Low/Medium/High based on data"
    }}
  ],
  "trending_topics_to_cover": ["topic1", "topic2", "topic3"],
  "format_combinations": [
    {{"formats": [1, 4], "rationale": "Why combining these formats works well"}}
  ]
}}
"""
