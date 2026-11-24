const labels: Record<string, string> = {
  Adventure: "Avventura", "City Car": "Auto da città", "Classic Scooter": "Scooter classico",
  Crossover: "Multistrada", Custom: "Personalizzata", "Electric Maxi Scooter": "Maxiscooter elettrico",
  "Electric Urban Scooter": "Scooter urbano elettrico", "GT Scooter": "Scooter da gran turismo",
  Hatchback: "Berlina compatta", "High Wheel Scooter": "Scooter a ruote alte",
  "Maxi Scooter": "Maxiscooter", Naked: "Senza carenatura", SUV: "Veicolo rialzato",
  "Sport Touring": "Turismo sportivo", "Station Wagon": "Familiare",
  "Touring Adventure": "Turismo e avventura", "Urban Scooter": "Scooter urbano",
};

/** Translate presentation only: canonical dataset category values stay untouched. */
export function categoryLabel(value: string): string {
  return labels[value] ?? value;
}

export function categoryText(value: string): string {
  return Object.keys(labels).sort((a, b) => b.length - a.length)
    .reduce((text, key) => text.replaceAll(key, categoryLabel(key)), value);
}