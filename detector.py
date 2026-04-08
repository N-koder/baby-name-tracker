import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ─── BABY-RELATED KEYWORD LISTS ──────────────────────────────────────────────

# English keywords
BABY_KEYWORDS_EN = [
    "baby", "newborn", "new born", "infant", "born", "birth", "delivery",
    "pregnant", "pregnancy", "expecting", "due date", "baby name", "named",
    "welcome", "bundle of joy", "little one", "baby girl", "baby boy",
    "daughter", "son", "mama", "daddy", "mommy", "father", "mother",
    "nursery", "baby shower", "congratulations", "congrats", "announce",
    "announcement", "arrived", "welcome to the world", "she/he is here",
    "healthy baby", "weight", "lbs", "kg born", "labour", "labor",
    "hospital", "maternity", "midwife", "ultrasound", "scan",
    "we are parents", "our baby", "our child", "she's here", "he's here"
]

# Thai keywords (Thai language — common for the example account)
BABY_KEYWORDS_TH = [
    "ลูก", "เด็ก", "ทารก", "คลอด", "คลอดลูก", "ตั้งครรภ์", "ท้อง",
    "แม่", "พ่อ", "แม่ลูก", "ลูกน้อย", "ลูกสาว", "ลูกชาย",
    "ชื่อลูก", "ยินดี", "ยินดีด้วย", "ต้อนรับ", "น้องใหม่",
    "คุณแม่", "คุณพ่อ", "เกิด", "ตั้งชื่อ", "ชื่อ", "น้อง",
    "คลินิก", "โรงพยาบาล", "รพ", "หมอ", "พยาบาล",
    "น้ำหนัก", "กิโล", "กรัม", "เซ็นติเมตร", "ส่วนสูง"
]

# Japanese keywords
BABY_KEYWORDS_JA = [
    "赤ちゃん", "赤ん坊", "出産", "誕生", "生まれ", "子供", "赤子",
    "名前", "命名", "誕生日", "妊娠", "出産報告", "産まれ", "ベビー"
]

# Korean keywords
BABY_KEYWORDS_KO = [
    "아기", "신생아", "출산", "탄생", "태어났", "이름", "작명",
    "임신", "출산 소식", "아들", "딸", "아기 이름"
]

# Chinese keywords
BABY_KEYWORDS_ZH = [
    "宝宝", "婴儿", "出生", "生了", "小孩", "新生", "取名", "孩子",
    "生产", "顺产", "剖腹产", "宝贝", "妈妈", "爸爸", "诞生"
]

# High-confidence patterns (regex)
HIGH_CONFIDENCE_PATTERNS = [
    r'\bnamed?\s+[A-Z][a-z]+\b',               # "named Alex"
    r'\bwelcome[d]?\s+\w+\s+to\s+the\s+world', # "welcomed ... to the world"
    r'\bborn\s+(?:on|at|in|weighing)\b',        # "born on/at/weighing"
    r'\b\d+\s*(?:lbs?|kg|pounds?|kilos?)\b',    # weight at birth
    r'\bit\'s\s+a\s+(?:girl|boy)\b',            # "it's a girl/boy"
    r'\bour\s+(?:new\s+)?(?:baby|son|daughter)\b',  # "our baby/son/daughter"
    r'\bwe\s+(?:are\s+)?(?:proud|happy|excited)\s+to\s+(?:announce|introduce|welcome)',
]

ALL_KEYWORDS = (
    BABY_KEYWORDS_EN
    + BABY_KEYWORDS_TH
    + BABY_KEYWORDS_JA
    + BABY_KEYWORDS_KO
    + BABY_KEYWORDS_ZH
)


class BabyDetector:

    def analyze(self, text: str) -> Dict:
        """
        Analyze a post for baby-related content.
        Returns detection result with translation and extracted names.
        """
        if not text or not text.strip():
            return {"is_baby_related": False}

        # Step 1: Translate to English
        translated = self._translate(text)

        # Step 2: Check keywords in both original and translated
        combined = text.lower() + " " + translated.lower()
        found_keywords = self._find_keywords(combined)

        # Step 3: Check high-confidence regex patterns
        pattern_matches = self._check_patterns(combined)

        # Step 4: Calculate confidence
        keyword_score = min(len(found_keywords) * 20, 60)
        pattern_score = min(len(pattern_matches) * 25, 40)
        confidence = min(keyword_score + pattern_score, 100)

        is_baby_related = confidence >= 20 or bool(pattern_matches)

        # Step 5: Extract possible baby names
        baby_names = []
        if is_baby_related:
            baby_names = self._extract_names(text, translated)

        return {
            "is_baby_related": is_baby_related,
            "confidence": confidence,
            "translated_text": translated if translated != text else text,
            "keywords_found": found_keywords[:5],
            "baby_names": baby_names,
            "original_text": text[:500]
        }

    def _translate(self, text: str) -> str:
        """Translate text to English using multiple fallback methods."""
        # Method 1: googletrans
        try:
            from googletrans import Translator
            translator = Translator()
            result = translator.translate(text, dest="en")
            if result and result.text:
                return result.text
        except Exception as e:
            logger.warning(f"googletrans failed: {e}")

        # Method 2: deep-translator
        try:
            from deep_translator import GoogleTranslator
            translated = GoogleTranslator(source="auto", target="en").translate(text[:4999])
            if translated:
                return translated
        except Exception as e:
            logger.warning(f"deep-translator failed: {e}")

        # Method 3: translate library
        try:
            from translate import Translator as T2
            t = T2(to_lang="en")
            return t.translate(text[:500])
        except Exception as e:
            logger.warning(f"translate lib failed: {e}")

        # Fallback: return original
        return text

    def _find_keywords(self, text: str) -> List[str]:
        found = []
        for kw in ALL_KEYWORDS:
            if kw.lower() in text:
                found.append(kw)
        return list(dict.fromkeys(found))  # dedupe preserving order

    def _check_patterns(self, text: str) -> List[str]:
        matches = []
        for pattern in HIGH_CONFIDENCE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                matches.append(pattern)
        return matches

    def _extract_names(self, original: str, translated: str) -> List[str]:
        """Extract possible baby names from text using NER and pattern matching."""
        names = []

        # Pattern: "named X" or "name is X" or "call him/her X"
        name_patterns = [
            r'\bnamed?\s+([A-Z][a-z]{1,15})\b',
            r'\bname\s+(?:is|was|will\s+be)\s+([A-Z][a-z]{1,15})\b',
            r'\bcall(?:ed|ing)?\s+(?:him|her|them|it)?\s*([A-Z][a-z]{1,15})\b',
            r'\bintroduc(?:e|ing|ed)\s+(?:you\s+to\s+)?([A-Z][a-z]{1,15})\b',
            r'\bwelcome\s+([A-Z][a-z]{1,15})\b',
            r'\bchose\s+(?:the\s+name\s+)?([A-Z][a-z]{1,15})\b',
            r'\bชื่อ\s*([\u0E00-\u0E7F]+)',   # Thai: "ชื่อ <name>"
            r'\bตั้งชื่อ\s*([\u0E00-\u0E7F]+)',  # Thai: "ตั้งชื่อ <name>"
        ]

        for text in [translated, original]:
            for pattern in name_patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    name = match.group(1).strip()
                    if name and name not in names and len(name) >= 2:
                        names.append(name)

        # Try spaCy NER for proper nouns after "named"
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(translated[:1000])
            for ent in doc.ents:
                if ent.label_ == "PERSON" and ent.text not in names:
                    # Only include if near baby keyword
                    context = translated[max(0, ent.start_char-50):ent.end_char+50].lower()
                    if any(kw in context for kw in ["baby", "born", "named", "name", "son", "daughter"]):
                        names.append(ent.text)
        except Exception:
            pass  # spaCy optional

        return names[:5]  # Return top 5 candidates
