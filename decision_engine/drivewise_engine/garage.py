from .utils import clamp

def garage_fit(profile, vehicle):
    if not profile.garage:
        return {"score":75.0,"status":"unknown","margins_mm":{}}
    g=profile.garage; d=vehicle.get("dimensions",{})
    width=d.get("width_with_mirrors_mm") or d.get("width_mm",0)
    margins={
        "length":g.get("length_mm",0)-d.get("length_mm",0),
        "door_width":g.get("door_width_mm",0)-width,
        "height":g.get("door_height_mm",0)-d.get("height_mm",0),
    }
    if min(margins.values())<0:
        return {"score":0.0,"status":"does_not_fit","margins_mm":margins}
    ls=clamp(margins["length"]/6,0,100)
    ws=clamp(margins["door_width"]/2.5,0,100)
    hs=clamp(margins["height"]/4,0,100)
    score=0.35*ls+0.45*ws+0.20*hs
    status="fits_comfortably" if score>=80 else "fits_tight" if score>=50 else "fits_very_tight"
    return {"score":round(score,1),"status":status,"margins_mm":margins}
