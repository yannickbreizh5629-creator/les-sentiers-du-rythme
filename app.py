import hashlib
import html
import json
import tempfile
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from engine import analyze, read_odt, export_json
from sequence import sequence_stats

st.set_page_config(page_title='Les Sentiers du rythme', layout='wide')
st.title('Les Sentiers du rythme')
st.caption('Prototype V0.3 · Du lustre, pas du lissage ! · Observation descriptive, jamais jugement littéraire.')
st.info('Confidentialité : en version web, les fichiers importés sont transmis au serveur pour analyse. '
        'L’application ne les enregistre pas volontairement dans une base de données ; '
        'ils peuvent toutefois rester temporairement en mémoire ou dans les mécanismes techniques de l’hébergeur. '
        'Évitez de transmettre un manuscrit confidentiel sans avoir évalué ce risque.')

sample = Path(__file__).parent / 'exemple_demo.txt'
source = st.sidebar.radio('Source', ['Texte de démonstration', 'Importer un ODT', 'Coller un texte'])
if source == 'Texte de démonstration':
    texts = sample.read_text(encoding='utf-8').split('\n')
    st.sidebar.caption('Exemple original de démonstration, sans extrait de manuscrit.')
elif source == 'Importer un ODT':
    uploaded = st.sidebar.file_uploader('Document ODT', type=['odt'])
    if uploaded is None:
        st.info('Importe un fichier ODT pour afficher sa partition.')
        st.stop()
    if uploaded.size > 10 * 1024 * 1024:
        st.error('Fichier trop volumineux (limite : 10 Mo).')
        st.stop()
    with tempfile.NamedTemporaryFile(suffix='.odt') as tmp:
        tmp.write(uploaded.getvalue())
        tmp.flush()
        texts = read_odt(tmp.name)
else:
    raw = st.text_area('Texte à explorer (une ligne = un bloc)', height=220)
    texts = raw.split('\n')

blocks = analyze(texts)
if not blocks:
    st.info('Aucun bloc à afficher.')
    st.stop()
if len(blocks) > 2500:
    st.warning('Document volumineux : un chapitre à la fois est recommandé.')

source_key = hashlib.sha256('\n'.join(texts).encode('utf-8')).hexdigest()
if st.session_state.get('source_key') != source_key:
    st.session_state.source_key = source_key
    st.session_state.focus = 1
    st.session_state.interval = (1, min(12, len(blocks)))
    st.session_state.grouped = False
    st.session_state.pop('range_slider', None)
    st.session_state.pop('partition', None)
    st.session_state.pop('condensed_chart', None)
    st.session_state.notes = {}
    st.session_state.group_anchor = None

c1, c2, c3, c4 = st.columns(4)
c1.metric('Blocs', len(blocks))
c2.metric('Paragraphes non vides', sum(b.kind in ('paragraphe', 'dialogue') for b in blocks))
c3.metric('Mots', sum(b.words for b in blocks))
c4.metric('Silences autonomes', sum(b.kind == 'silence' for b in blocks))

st.subheader('Partition chronologique')
st.caption('Une barre = un bloc dans son ordre d’apparition. Cliquer sur une barre sélectionne son texte. Le zoom Plotly reste disponible.')
df = pd.DataFrame([{'position': b.index + 1, 'mots': b.words, 'type': b.kind,
                    'texte': b.text[:180] or '[blanc]'} for b in blocks])
colors = {'paragraphe': '#4878a8', 'dialogue': '#e39a47', 'silence': '#a45175', 'blanc': '#a0a0a0'}
fig = px.bar(df, x='position', y='mots', color='type', hover_data=['texte'],
             category_orders={'type': ['paragraphe', 'dialogue', 'silence', 'blanc']},
             color_discrete_map=colors)
fig.update_traces(customdata=None)
fig.update_layout(xaxis_title='Position du bloc dans le texte', yaxis_title='Nombre de mots',
                  legend_title='Nature du bloc', height=380, clickmode='event+select')
fig.update_xaxes(dtick=max(1, len(blocks)//25))
# streamlit >= 1.35 permet la sélection directe des points Plotly.
event = st.plotly_chart(fig, use_container_width=True, key='partition',
                        on_select='rerun', selection_mode='points')
points = event.selection.points if event is not None else []
if points:
    pos = int(round(points[-1]['x']))
    if 1 <= pos <= len(blocks):
        st.session_state.focus = pos

# La sélection d'une barre de la partition principale pilote le bloc actif.
# Les commandes de plage sont indépendantes du zoom Plotly.
st.caption(f'Bloc actif : **{st.session_state.focus}**. Cliquez sur une barre pour le changer.')
a, z, clear = st.columns([1, 1, 1])
if a.button('Début du groupe = bloc actif', use_container_width=True):
    old_a, old_z = st.session_state.interval
    st.session_state.interval = (min(st.session_state.focus, old_z), max(st.session_state.focus, old_z))
    st.session_state.pop('range_slider', None)
    st.rerun()
if z.button('Fin du groupe = bloc actif', use_container_width=True):
    old_a, old_z = st.session_state.interval
    st.session_state.interval = (min(old_a, st.session_state.focus), max(old_a, st.session_state.focus))
    st.session_state.pop('range_slider', None)
    st.rerun()
if clear.button('Revenir au bloc actif', use_container_width=True):
    st.session_state.interval = (st.session_state.focus, st.session_state.focus)
    st.session_state.pop('range_slider', None)
    st.rerun()

st.subheader('Examiner une séquence')
st.caption('Choisis un intervalle de blocs consécutifs. Les statistiques sont calculées sur cet intervalle, sans fusionner les paragraphes.')
if len(blocks) > 1:
    start, end = st.slider('Intervalle de blocs (bornes incluses)', min_value=1,
                           max_value=len(blocks), value=st.session_state.interval,
                           key='range_slider')
else:
    start = end = 1
st.session_state.interval = (start, end)

stats = sequence_stats(blocks, start, end)
cols = st.columns(5)
cols[0].metric('Blocs sélectionnés', stats['blocs'])
cols[1].metric('Mots', stats['mots'])
cols[2].metric('Moyenne (hors blancs)', f"{stats['moyenne']:.1f}")
cols[3].metric('Écart-type (hors blancs)', f"{stats['ecart_type']:.1f}")
cols[4].metric('Silences', stats['silences'])
st.caption(f"Médiane : {stats['mediane']:g} · Min–max : {stats['minimum']}–{stats['maximum']} mots · "
           f"Dialogues : {stats['dialogues']} · Blancs : {stats['blancs']}. "
           'La moyenne et la dispersion portent sur les paragraphes et dialogues non vides.')

selected = blocks[start-1:end]
local_df = pd.DataFrame([{'position': b.index + 1, 'mots': b.words, 'type': b.kind} for b in selected])
local_fig = px.bar(local_df, x='position', y='mots', color='type', color_discrete_map=colors,
                   category_orders={'type': ['paragraphe', 'dialogue', 'silence', 'blanc']})
local_fig.update_layout(height=260, showlegend=False, xaxis_title='Position originale',
                        yaxis_title='Mots', bargap=.12)
local_fig.update_xaxes(dtick=1 if len(selected) <= 30 else max(1, len(selected)//20))
st.plotly_chart(local_fig, use_container_width=True)

st.markdown('**Ponctuation de la séquence**')
if stats['ponctuation']:
    st.dataframe(pd.DataFrame([{'Signe': k, 'Occurrences': v} for k, v in stats['ponctuation'].items()]),
                 hide_index=True, use_container_width=True)
else:
    st.caption('Aucune ponctuation détectée dans cette sélection.')

st.subheader('Regroupement réversible')
show_group = st.toggle('Afficher les blocs sélectionnés comme un groupe', key='grouped')
if show_group:
    st.info(f'Groupe {start}–{end} · {stats["mots"]} mots · {stats["blocs"]} blocs. '
            'Le regroupement ne modifie jamais le texte original.')

    st.markdown('**Partition condensée : une barre pour le groupe**')
    condensed = []
    for block in blocks:
        position = block.index + 1
        if position == start:
            condensed.append({'position': start, 'mots': stats['mots'], 'type': 'groupe',
                              'libellé': f'Groupe {start}–{end} ({stats["blocs"]} blocs)'})
        if start <= position <= end:
            continue
        condensed.append({'position': position, 'mots': block.words, 'type': block.kind,
                          'libellé': f'Bloc {position}'})
    condensed_df = pd.DataFrame(condensed)
    condensed_colors = {**colors, 'groupe': '#8b5cf6'}
    condensed_fig = px.bar(condensed_df, x='position', y='mots', color='type',
                           hover_data=['libellé'], color_discrete_map=condensed_colors,
                           category_orders={'type': ['paragraphe', 'dialogue', 'silence', 'blanc', 'groupe']})
    condensed_fig.update_layout(height=320, xaxis_title='Position originale (début du groupe)',
                                yaxis_title='Mots (somme dans le groupe)',
                                legend_title='Nature du bloc')
    condensed_fig.update_xaxes(dtick=max(1, len(blocks)//25))
    condensed_event = st.plotly_chart(condensed_fig, use_container_width=True,
                                     key='condensed_chart', on_select='rerun', selection_mode='points')
    condensed_points = condensed_event.selection.points if condensed_event is not None else []
    if condensed_points:
        pos = int(round(condensed_points[-1]['x']))
        if 1 <= pos <= len(blocks):
            st.session_state.focus = pos
    st.caption('La barre violette représente le total du groupe, non une phrase unique. '
               'La partition détaillée ci-dessus conserve toutes les frontières et les contrastes.')

    st.markdown('**Texte continu de la séquence**')
    st.caption('Les blocs sont dans leur ordre original. Un liseré indique le bloc actif ; '
               'les espaces et les silences autonomes restent visibles.')
    paragraphs = []
    for block in selected:
        pos = block.index + 1
        active = pos == st.session_state.focus
        bg = 'background:rgba(139,92,246,0.12);border-left:4px solid #8b5cf6;' if active else 'border-left:4px solid transparent;'
        if block.kind == 'blanc':
            content = '&nbsp;'
            style = 'min-height:1.4em;'
        else:
            content = html.escape(block.text).replace('\n', '<br>')
            style = ''
        paragraphs.append(f'<div title="Bloc {pos} · {block.kind} · {block.words} mots" '
                          f'style="{bg}{style}padding:5px 12px;margin:0 0 3px 0;'
                          f'white-space:pre-wrap;overflow-wrap:anywhere;">{content}</div>')
    st.markdown('<div style="max-height:530px;overflow-y:auto;line-height:1.7;'
                'padding:12px;border:1px solid #aaa5;border-radius:8px">'
                + ''.join(paragraphs) + '</div>', unsafe_allow_html=True)
    st.caption('Pour examiner un bloc du passage, choisissez son numéro ci-dessous. '
               'La sélection est surlignée dans le texte continu.')
    choices = list(range(start, end+1))
    active_in_range = st.session_state.focus if st.session_state.focus in choices else start
    chosen = st.selectbox('Bloc du groupe à examiner', choices,
                          index=choices.index(active_in_range),
                          format_func=lambda i: f'Bloc {i} · {blocks[i-1].kind} · {blocks[i-1].words} mots')
    if st.button('Examiner ce bloc dans le détail'):
        st.session_state.focus = chosen
        st.rerun()
    with st.expander('Voir les blocs séparément (structure d’origine)'):
        for block in selected:
            st.markdown(f'**Bloc {block.index+1} · {block.kind} · {block.words} mot(s)**')
            st.code(block.text if block.text else '[blanc]', language=None)
else:
    st.caption('Vue détaillée active : activez le regroupement pour voir la barre condensée et le texte continu.')

st.subheader('Retour au texte et ponctuation')
focus = st.number_input('Bloc à examiner (position)', min_value=1, max_value=len(blocks),
                        value=int(st.session_state.focus), step=1)
st.session_state.focus = focus
b = blocks[focus - 1]
st.markdown(f'**Bloc {focus} · {b.kind} · {b.words} mot(s)**')
st.code(b.text if b.text else '[blanc]', language=None)
if b.segments:
    st.dataframe(pd.DataFrame([{'Segment': s['text'], 'Mots': s['words'],
                                'Ponctuation suivante': s['end_mark']} for s in b.segments]),
                 hide_index=True, use_container_width=True)
if b.marks:
    st.caption('Ponctuations repérées : ' + ' · '.join(
        f"{m['mark']} (caractère {m['offset']+1})" for m in b.marks))

st.subheader('Notes de lecture')
notes = st.text_area('Annotation personnelle pour ce bloc',
                     value=st.session_state.notes.get(str(focus), ''), key=f'note_{focus}')
if st.button('Enregistrer la note pour ce bloc'):
    st.session_state.notes[str(focus)] = notes
    st.success('Note conservée pendant cette session. Pense à exporter les annotations.')

exported = {'selection': {'debut': start, 'fin': end}, 'statistiques': stats,
            'blocs': export_json(selected)}
st.download_button('Exporter les mesures de la séquence (JSON)',
                   json.dumps(exported, ensure_ascii=False, indent=2).encode('utf-8'),
                   file_name='sequence_mesures.json', mime='application/json')
st.download_button('Exporter toutes les mesures (JSON)',
                   json.dumps(export_json(blocks), ensure_ascii=False, indent=2).encode('utf-8'),
                   file_name='partition_mesures.json', mime='application/json')
st.download_button('Exporter les annotations (JSON)',
                   json.dumps(st.session_state.notes, ensure_ascii=False, indent=2).encode('utf-8'),
                   file_name='annotations.json', mime='application/json')

with st.expander('Limites et conventions de la V0.3'):
    st.write('Le regroupement est **visuel et statistique** : aucun bloc n’est modifié. La barre du groupe montre un total, pas une longueur de phrase. '
             'La segmentation est ponctuationnelle, non syntaxique. Le comptage des mots suit '
             'une convention simple. Les styles ODT et les sauts de ligne internes ne sont pas '
             'encore entièrement préservés. Les blancs et les silences restent dans leur ordre. '
             'Les statistiques ne mesurent pas la durée réelle des pauses ni les émotions.')
