/** Illustrative home story, separate from the live vehicle ranking. */
export const homeExample = {
  score: 88,
  confidence: 76,
  budget: 35_000,
  price: 34_000,
  name: "Station wagon ibrida",
  category: "Station wagon",
  strengths: [
    "Bagagliaio da 608 L",
    "Entra nel box con 12 cm di margine",
    "Costi d'uso bassi: 5,1 l/100 km",
  ],
  tradeoffs: ["Accelerazione tranquilla", "Tre seggiolini dietro: solo 2 + 1 stretto"],
} as const;