#!/usr/bin/env python3
"""Generate original SVG assets from public synthetic data; standard library only."""
from fractions import Fraction as F
from html import escape
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from crossroads_state import Engine, Operation, State
from crossroads_state.synthetic import fixture_state

NIGHT, INK = "#0D0D1B", "#F0EAF7"
PURPLE, GREEN, GOLD, MUTED = "#AC88E2", "#73DAB1", "#E8C985", "#AAA6BD"


def text(x, y, content, size=22, fill=INK, font="Arial, sans-serif", **attributes):
    attrs = " ".join(f'{k.replace("_", "-")}="{escape(str(v))}"' for k, v in attributes.items())
    return f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{fill}" {attrs}>{escape(str(content))}</text>'


def line(x1, y1, x2, y2, color, width=1, opacity=1, **attributes):
    attrs = " ".join(f'{k.replace("_", "-")}="{escape(str(v))}"' for k, v in attributes.items())
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}" opacity="{opacity}" {attrs}/>'


def circle(x, y, radius, fill, stroke="none", width=1, opacity=1):
    return f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" opacity="{opacity}"/>'


def opening(width, height, title, description):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>',
            '<defs><radialGradient id="nightglow"><stop stop-color="#281D3C"/><stop offset="1" stop-color="#0D0D1B"/></radialGradient>',
            '<linearGradient id="sweep"><stop stop-color="#AC88E2"/><stop offset=".55" stop-color="#73DAB1"/><stop offset="1" stop-color="#E8C985"/></linearGradient>',
            '<filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="5"/></filter>',
            '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10" fill="#73DAB1"/></marker>',
            '<marker id="goldarrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10" fill="#E8C985"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="{NIGHT}"/>']


def banner():
    state = fixture_state()
    out = opening(1800, 620, "Crossroads State - TASUMER MAF",
                  "Exact state, partial observation, reversible recovery. An indexed 81-value public synthetic field, its nine-address reader and carried reference.")
    out += ['<rect x="860" width="940" height="620" fill="url(#nightglow)"/>',
            '<rect x="36" y="36" width="1728" height="548" rx="2" fill="none" stroke="#8D77A9" stroke-opacity=".24"/>',
            line(76, 94, 850, 94, GOLD, 1, .5),
            text(78, 74, "TASUMER MAF  /  RESEARCH INSTRUMENTS", 18, GOLD, letter_spacing=3.7),
            text(74, 220, "Crossroads", 104, INK, "Georgia, serif"),
            text(78, 327, "State", 104, INK, "Georgia, serif"),
            text(82, 386, "Exact state · Partial observation · Reversible recovery", 23, MUTED),
            line(82, 433, 830, 433, PURPLE, 1, .35)]
    for x, count, label, color in [(82, "512", "EXACT RETURNS", GREEN), (340, "20,480", "CHECKED STEPS", PURPLE), (610, "3,402", "PRIMITIVE CASES", GOLD)]:
        out += [text(x, 487, count, 36, color, "Georgia, serif"),
                text(x, 516, label, 13, MUTED, letter_spacing=2)]
    out += [text(82, 555, "SYNTHETIC STUDY  /  STANDARD LIBRARY  /  NO MODEL INFERENCE", 12, MUTED, letter_spacing=1.5)]
    # Isometric arrangement of a 9 x 9 index table, not a claim of physical geometry.
    def position(index):
        row, col = divmod(index, 9)
        return (1352 + (col-row)*35, 155 + (col+row)*18)
    for row in range(9):
        for col in range(9):
            x, y = position(row*9+col)
            value = state.values[row*9+col]
            color = GREEN if value >= 11 else PURPLE
            intensity = .16 + min(float(abs(value-11))/12, .5)
            points = f'{x},{y-14} {x+28},{y} {x},{y+14} {x-28},{y}'
            out.append(f'<polygon points="{points}" fill="{color}" fill-opacity="{intensity:.3f}" stroke="{color}" stroke-opacity=".27"/>')
            out.append(circle(x,y,1.4,color,opacity=.6))
    route = [position(i) for i in state.reader]
    out.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in route)+'" fill="none" stroke="'+GREEN+'" stroke-width="2.2" opacity=".8"/>')
    for ordinal,(x,y) in enumerate(route,1):
        out += [circle(x,y,7,GREEN,opacity=.2),circle(x,y,3.2,GREEN),
                text(x+10,y+4,ordinal,11,GREEN)]
    x,y=position(state.reference)
    out += [circle(x,y,22,"none",GOLD,1.3),circle(x,y,31,"none",GOLD,.7,.35),
            line(x-39,y,x-25,y,GOLD,1,.8),line(x+25,y,x+39,y,GOLD,1,.8),
            line(x,y-39,x,y-25,GOLD,1,.8),line(x,y+25,x,y+39,GOLD,1,.8),
            text(1352,112,"81 ADDRESSES · EXACT RATIONAL FIELD",13,MUTED,text_anchor="middle",letter_spacing=2),
            circle(1124,493,4,PURPLE),text(1136,499,"FIELD",14,MUTED,letter_spacing=1.5),
            circle(1266,493,4,GREEN),text(1278,499,"READER",14,MUTED,letter_spacing=1.5),
            circle(1432,493,4,GOLD),text(1444,499,"REFERENCE",14,MUTED,letter_spacing=1.5),
            line(1068,528,1636,528,GOLD,.7,.35),
            text(1352,555,"Keep the field. Keep the reading. Keep the reference.",16,MUTED,text_anchor="middle"),
            '</svg>']
    return "\n".join(out)


def state_diagram():
    engine = Engine(4,2,{"relabel":Operation(permutation=(1,2,3,0),reframe=True)}, name="public-diagram-four-cycle")
    start = State(tuple(map(F,(2,7,-3,5))),(0,3),1)
    arrival = engine.step(start,"relabel",1)
    assert start.observe()==arrival.observe() and engine.step(arrival,"relabel",-1)==start
    out=opening(1500,710,"What a passive coordinate change preserves",
                "A four-address exact state is relabeled by one step. Values, ordered reader and reference move together; the observed pair remains 2,5. The inverse restores the complete initial state.")
    out += [text(52,66,"ONE OPERATION. THREE THINGS MOVE.",19,GOLD,letter_spacing=2.2),
            text(52,116,"The reading stays the same. The address labels change.",34,INK,"Georgia, serif")]
    def panel(x,state,title):
        parts=[f'<rect x="{x}" y="158" width="580" height="357" rx="12" fill="#161423" stroke="#5D4B74" stroke-opacity=".65"/>',
               text(x+30,204,title,18,PURPLE,letter_spacing=2)]
        for i,value in enumerate(state.values):
            cx=x+87+i*133
            parts += [text(cx,252,f"address {i}",14,MUTED,text_anchor="middle"),
                      f'<rect x="{cx-47}" y="268" width="94" height="86" rx="5" fill="#241D33" stroke="#74608E"/>',
                      text(cx,323,str(value),36,INK,"Georgia, serif",text_anchor="middle")]
            if i in state.reader:
                parts += [f'<rect x="{cx-48}" y="267" width="96" height="88" rx="5" fill="none" stroke="{GREEN}" stroke-width="2"/>',
                          circle(cx,376,12,GREEN),text(cx,381,state.reader.index(i)+1,13,NIGHT,text_anchor="middle",font_weight="bold")]
            if i==state.reference:
                parts += [circle(cx,310,57,"none",GOLD,1.3),
                          text(cx,418,"reference",14,GOLD,text_anchor="middle")]
        reader=" → ".join(str(i) for i in state.reader)
        result=", ".join(str(v) for v in state.observe())
        parts += [line(x+29,439,x+551,439,PURPLE,1,.3),
                  text(x+30,473,"READ IN ORDER",12,MUTED,letter_spacing=1.5),
                  text(x+177,475,reader,19,GREEN),
                  text(x+355,475,f"observed ({result})",18,INK)]
        return parts
    out+=panel(52,start,"INITIAL STATE")+panel(868,arrival,"RELABELLED STATE")
    out += [line(666,316,842,316,GREEN,2,1,marker_end="url(#arrow)"),
            text(754,278,"relabel +1",19,GREEN,text_anchor="middle"),
            text(754,352,"old address i",14,MUTED,text_anchor="middle"),
            text(754,377,"becomes i + 1",14,MUTED,text_anchor="middle"),
            text(754,402,"3 wraps to 0",14,MUTED,text_anchor="middle"),
            '<path d="M1158,535 L1158,569 Q1158,588 1139,588 L362,588 Q343,588 343,569 L343,535" fill="none" stroke="'+GOLD+'" stroke-width="1.6" marker-end="url(#goldarrow)"/>',
            f'<rect x="585" y="567" width="330" height="40" fill="{NIGHT}"/>',
            text(750,591,"inverse −1 · complete return",19,GOLD,text_anchor="middle"),
            text(52,661,"PURPLE  values at every address",15,PURPLE),
            text(527,661,"GREEN  reader order",15,GREEN),
            text(931,661,"GOLD  carried reference",15,GOLD),
            '</svg>']
    data={"model":"generic-four-cycle", "initial":start.plain(),"after_relabel_plus_one":arrival.plain(),
          "initial_observation":list(map(str,start.observe())),"arrival_observation":list(map(str,arrival.observe())),
          "inverse_full_return":True,"meaning":"Passive relabeling, not a change of the observed pair or a recovery of route history"}
    return "\n".join(out),data


def main():
    destination=ROOT/'assets';destination.mkdir(exist_ok=True)
    (destination/'banner.svg').write_text(banner())
    diagram,data=state_diagram()
    (destination/'state-contract.svg').write_text(diagram)
    (destination/'state-contract.json').write_text(json.dumps(data,indent=2)+'\n')
    print("Generated two original SVGs and their four-address demonstration record")


if __name__=='__main__':main()
