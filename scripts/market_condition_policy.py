"""Conservative condition interpretation for explicitly single-card listings.

A missing condition is an *assumption*, never a verified Near Mint grade.
Only German offers use that fallback during this rollout.
"""
import re

POSITIVE={'near mint','nearmint','nm','mint','m','neu','neuwertig','wie neu','excellent mint'}
NEGATIVE={'played','light played','lightly played','moderately played','heavily played','poor','good','gd','lp','mp','hp','damaged','dmg','excellent','ex','pl','played condition','beschädigt','beschaedigt','gebraucht','stark gespielt','gespielt','gut','mäßig','maessig','schlecht'}

def classify_condition(value,*,language='de'):
    """Return explicit_nm / assumed_nm / rejected / unknown.

    Never infer NM from a recognized non-NM descriptor or an unknown label.
    """
    if value is None or not str(value).strip():
        return 'assumed_nm' if language == 'de' else 'unknown'
    text=re.sub(r'\s+',' ',str(value).strip().lower().replace('_',' ').replace('-',' '))
    if text in POSITIVE:return 'explicit_nm'
    if text in NEGATIVE:return 'rejected'
    return 'unknown'
