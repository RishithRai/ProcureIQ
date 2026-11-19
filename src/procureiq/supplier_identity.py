"""Versioned conservative rules; keys are not proof of legal identity."""
import re

PLACEHOLDERS = {'', 'n/a', 'na', 'none', 'null', 'unknown', 'not known', 'not available',
                'not applicable', 'not disclosed', 'withheld', 'name withheld', 'supplier withheld',
                'redacted', '[redacted]', 'redacted supplier', 'various', 'various suppliers',
                'confidential', 'individual', 'private individual'}


def matching_key(name):
    return ' '.join(name.casefold().split())


def is_placeholder(name):
    key = matching_key(name)
    return (key in PLACEHOLDERS or bool(re.fullmatch(r'[\s*\-x]+', key))
            or bool(re.match(r'^\[?redacted(?:\]|\b)', key)))


def identity(name):
    key = matching_key(name)
    unresolved = is_placeholder(name)
    return dict(original_name=name, normalized_key=key,
                mapping_method='placeholder_v1' if unresolved else 'case_whitespace_v1',
                review_status='unresolved' if unresolved else 'auto_resolved')


def punctuation_candidates(names):
    groups = {}
    for name in sorted(set(names)):
        if not is_placeholder(name):
            groups.setdefault(re.sub(r'[^\w]', '', matching_key(name)), []).append(name)
    return [dict(review_key=k, original_names=v, reason='punctuation_similarity_no_merge')
            for k, v in sorted(groups.items()) if len({matching_key(n) for n in v}) > 1]
