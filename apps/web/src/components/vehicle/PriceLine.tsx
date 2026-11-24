import { formatListDate, formatListEur } from "@/components/vehicle/source-facts";
import { euro } from "@/lib/vehicle-format";
import type { Vehicle } from "@/services/vehicleService";

/** A list price is labelled as such; a base price without a list stays an indication. */
export function priceText(vehicle: Vehicle): string | null {
  const price = vehicle.list_price;
  if (price)
    return `Prezzo di listino ${formatListEur(price.price_eur)} · listino valido dal ${formatListDate(price.price_list_valid_from)}`;
  if (vehicle.pricing.new_price_estimate) return `Prezzo indicativo del nuovo ${euro(vehicle.pricing.new_price_estimate)}`;
  return null;
}

export function PriceLine({ vehicle, className = "mt-3 text-[0.95rem] text-muted-foreground" }: { vehicle: Vehicle; className?: string }) {
  const text = priceText(vehicle);
  return text ? <p className={className}>{text}</p> : null;
}
