from .utils import clamp
BASELINE_KM = 15000

def personalized_annual_tco(profile, vehicle):
    c = vehicle.get("ownership_costs", {})
    insurance=float(c.get("insurance_year_estimate",0) or 0)
    tax=float(c.get("tax_year_estimate",0) or 0)
    energy=float(c.get("fuel_energy_year_estimate",0) or 0)
    maintenance=float(c.get("maintenance_year_estimate",0) or 0)
    tyres=float(c.get("tyres_year_estimate",0) or 0)
    depreciation=float(c.get("depreciation_year_estimate",0) or 0)
    if any([insurance,tax,energy,maintenance,tyres,depreciation]):
        km_factor=max(0.4, profile.annual_km/BASELINE_KM)
        return round(
            insurance+tax+
            energy*km_factor+
            maintenance*(0.65+0.35*km_factor)+
            tyres*(0.55+0.45*km_factor)+
            depreciation,2
        )
    return float(c.get("total_year_estimate",0) or 0)

def tco_score(profile, vehicle):
    tco=personalized_annual_tco(profile,vehicle)
    target=max(profile.budget_max*0.22,3500)
    ratio=tco/target if target else 1
    if ratio<=0.85: return 100.0
    if ratio<=1.0: return 95.0
    return clamp(95-(ratio-1)*42)
