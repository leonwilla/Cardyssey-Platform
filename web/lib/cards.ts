/**
 * Placeholder card artwork. Replace `src`, `name` and `type` with authentic
 * Pokémon TCG assets – every card visual on the page reads from this list.
 */
export type CollectorCard = {
  id: string
  name: string
  type: string
  src: string
}

export const cards: CollectorCard[] = [
  { id: 'water', name: 'Aquaraura', type: 'Wasser', src: '/images/card-water.jpg' },
  { id: 'grass', name: 'Forest Keeper', type: 'Pflanze', src: '/images/card-grass.jpg' },
  { id: 'fire', name: 'Ignis Fox', type: 'Feuer', src: '/images/card-fire.jpg' },
  { id: 'electric', name: 'Zapsqueak', type: 'Elektro', src: '/images/card-electric.jpg' },
  { id: 'psychic', name: 'Stellar Flutter', type: 'Psycho', src: '/images/card-psychic.jpg' },
]

export function cardAlt(card: CollectorCard) {
  return `Sammelkarte ${card.name}, Typ ${card.type}`
}
