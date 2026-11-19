"""Bounded dynamic preview extracted from the actual generated editable PPTX.
This preserves slide content/positions, but is not pixel-exact Office rendering.
"""
from io import BytesIO
from pptx import Presentation

def slide_model(payload):
    prs=Presentation(BytesIO(payload));scale=1000/prs.slide_width
    slides=[]
    for slide in prs.slides:
        shapes=[]
        for shape in slide.shapes:
            item=dict(x=shape.left*scale,y=shape.top*scale,width=shape.width*scale,height=shape.height*scale)
            if shape.has_table:
                item.update(kind='table',rows=[[c.text for c in row.cells] for row in shape.table.rows])
            elif shape.has_chart:
                chart=shape.chart
                item.update(kind='chart',categories=[c.label for c in chart.plots[0].categories],values=list(chart.series[0].values),label=chart.series[0].name)
            elif shape.has_text_frame:
                runs=[r for p in shape.text_frame.paragraphs for r in p.runs]
                font=runs[0].font if runs else None
                if font is None or font.size is None:font=shape.text_frame.paragraphs[0].font
                item.update(kind='text',text=shape.text,font_size=(font.size.pt if font and font.size else 16)*1000/(40/3*72),bold=bool(font and font.bold))
            else:continue
            shapes.append(item)
        slides.append(dict(shapes=shapes))
    return dict(width=1000,height=prs.slide_height*scale,slides=slides,rendering='Dynamic content and layout preview extracted from the generated PPTX; not pixel-exact Microsoft Office rendering.')
