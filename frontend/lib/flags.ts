const CODES: Record<string, string> = {
  "Argentina": "ar", "France": "fr", "Brazil": "br", "Spain": "es",
  "England": "gb-eng", "Germany": "de", "Portugal": "pt", "Netherlands": "nl",
  "Italy": "it", "Belgium": "be", "Uruguay": "uy", "Colombia": "co",
  "Mexico": "mx", "United States": "us", "Canada": "ca", "Japan": "jp",
  "South Korea": "kr", "Morocco": "ma", "Senegal": "sn", "Ecuador": "ec",
  "Croatia": "hr", "Denmark": "dk", "Switzerland": "ch", "Austria": "at",
  "Sweden": "se", "Norway": "no", "Turkey": "tr", "Serbia": "rs",
  "Poland": "pl", "Czech Republic": "cz", "Scotland": "gb-sct", "Australia": "au",
  "New Zealand": "nz", "Saudi Arabia": "sa", "Iran": "ir", "Iraq": "iq",
  "Jordan": "jo", "Qatar": "qa", "Egypt": "eg", "Tunisia": "tn",
  "Ghana": "gh", "DR Congo": "cd", "Côte d'Ivoire": "ci", "South Africa": "za",
  "Nigeria": "ng", "Algeria": "dz", "Cape Verde": "cv", "Haiti": "ht",
  "Panama": "pa", "Honduras": "hn", "Venezuela": "ve", "Paraguay": "py",
  "Uzbekistan": "uz", "Bosnia and Herzegovina": "ba", "Curaçao": "cw",
  "Cameroon": "cm", "Costa Rica": "cr", "Russia": "ru",
}

export function flagCode(team: string): string {
  return CODES[team] ?? ""
}

export function flagUrl(team: string, size: "16x12" | "24x18" | "32x24" = "24x18"): string {
  const code = CODES[team]
  if (!code) return ""
  return `https://flagcdn.com/${size}/${code}.png`
}

// kept for backwards compat — returns empty string on Windows where emoji don't render
export function flag(_team: string): string {
  return ""
}
