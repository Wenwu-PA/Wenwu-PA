#!/usr/bin/env python3
"""Render a dependency-free GitHub profile widget using public REST API data."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]

def api(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'wenwu-profile-widget'}
    if token := os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + token
    with urlopen(Request('https://api.github.com' + path, headers=headers), timeout=30) as res:
        return json.load(res)

def fetch(user):
    base = '/users/' + quote(user, safe='')
    profile = api(base)
    repos = []
    page = 1
    while True:
        batch = api(f'{base}/repos?type=owner&per_page=100&page={page}')
        repos.extend(r for r in batch if not r['private'] and not r['fork'])
        if len(batch) < 100:
            break
        page += 1
    langs = Counter(r['language'] for r in repos if r.get('language') and r['name'].lower() != user.lower())
    recent = sorted((r for r in repos if r['name'].lower() != user.lower()), key=lambda r: r['pushed_at'] or '', reverse=True)
    return dict(repos=len(repos), stars=sum(r['stargazers_count'] for r in repos), followers=profile['followers'], langs=langs.most_common(4), recent=recent[0]['name'] if recent else '—', updated=datetime.now(timezone.utc).strftime('%Y-%m-%d'))

def render(user, data, light=False):
    bg, fg, muted, line = ('#f2eee5','#24231f','#625e55','#cfc7b9') if light else ('#11110f','#eee9df','#a39e94','#383630')
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="200" viewBox="0 0 640 200" role="img" aria-label="Public GitHub statistics for {escape(user)}">', f'<rect x=".5" y=".5" width="639" height="199" rx="5" fill="{bg}" stroke="{line}"/>', f'<g font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">']
    def t(x,y,s,size=12,color=fg,anchor='start'):
        out.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{escape(str(s))}</text>')
    def rule(x1,y1,x2,y2):
        out.append(f'<path d="M{x1} {y1}H{x2}" stroke="{line}"/>' if y1==y2 else f'<path d="M{x1} {y1}V{y2}" stroke="{line}"/>')
    t(20,24,'+--[ 02 / GITHUB TELEMETRY ]',12,muted); t(620,24,'@'+user,12,muted,'end')
    rule(20,36,620,36)
    for x,key,label in [(20,'repos','PUBLIC REPOS*'),(225,'stars','STARS'),(430,'followers','FOLLOWERS')]:
        t(x,56,label,10,muted); t(x,86,data[key],28)
    rule(208,48,208,90);rule(414,48,414,90);rule(20,100,620,100)
    t(20,119,'LANGUAGES / PRIMARY',10,muted); t(365,119,'LAST PUSH / REPOSITORY',10,muted)
    if data['langs']:
        for i,(name,count) in enumerate(data['langs']):
            y=136+i*13; t(20,y,str(name)[:13],11); t(139,y,'#'*min(12,count),10); t(326,y,count,11,muted,'end')
    else:
        t(20,140,'awaiting first sync',11,muted)
    t(365,140,data['recent'][:32],12)
    t(365,158,'SYNC: '+data['updated'],10,muted)
    t(365,178,'* OWNED / NO FORKS',10,muted)
    t(620,190,'[ 02 / W ]--+',10,muted,'end')
    out.append('</g></svg>')
    return '\n'.join(out)+'\n'

def main():
    p=argparse.ArgumentParser(); p.add_argument('--user',default='Wenwu-PA'); p.add_argument('--preview',action='store_true'); args=p.parse_args()
    data=dict(repos=21,stars='—',followers=3,langs=[],recent='awaiting first sync',updated='pending') if args.preview else fetch(args.user)
    (ROOT/'assets').mkdir(exist_ok=True)
    for mode in ('dark','light'):
        (ROOT/'assets'/f'github-{mode}.svg').write_text(render(args.user,data,mode=='light'),encoding='utf-8')

if __name__=='__main__': main()
