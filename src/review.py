"""Deterministic review priorities derived from an existing studio result.

No network calls, generated answers, or automatic operational changes.
"""
import json
PROJECT = 'datalens'
NAME = 'DataLens'

def attach(request, result):
    lab = result['lab']
    items = []

    def add(key, severity, title, detail):
        items.append({'id': key, 'severity': severity, 'title': title, 'detail': detail})
    governed = {c['column'] for c in lab['checks']}
    uncovered = [c for c in lab['columns'] if c not in governed]
    if uncovered:
        add('coverage', 'review', 'Columns without contracts', ', '.join(uncovered) + '. Choose rules deliberately; no suggested rule is applied automatically.')
    for c in lab['checks']:
        if c['failed']:
            add('contract-' + str(c['id']), 'high', c['column'] + ': ' + c['type'], str(c['failed']) + ' record(s) fail this contract. Inspect violations before changing the rule.')
    for d in lab['drift']:
        if d['status'] != 'stable':
            add('drift-' + d['column'], 'review', d['column'] + ': ' + d['status'], 'Compare the current and reference populations. PSI is a heuristic, not a significance test.')
    add('policy', 'info', 'Retain the contract policy', 'A passing rule does not establish dataset accuracy. Keep the rules, source snapshot, and violations together.')
    items.sort(key=lambda x: {'high': 0, 'review': 1, 'info': 2}[x['severity']])
    review = {'version': '2.1.0', 'project': PROJECT, 'name': NAME, 'items': items, 'summary': {level: sum((x['severity'] == level for x in items)) for level in ['high', 'review', 'info']}, 'scope': 'Deterministic review aid from this experiment. Checklist completion does not certify correctness, safety, production readiness, or privacy.'}
    report = '# ' + NAME + ' — review handoff\n\n' + review['scope'] + '\n\n'
    for item in items:
        title = item['title'].replace('\n', ' ').replace('\r', ' ')
        detail = item['detail'].replace('\n', ' ').replace('\r', ' ')
        report += '- [ ] [' + item['severity'].upper() + '] ' + title + '\n  ' + detail + '\n'
    result['review'] = review
    result['artifacts'] += [{'name': 'review-handoff.md', 'content': report}, {'name': 'review-priorities.json', 'content': json.dumps(review, indent=2)}]
    return result
