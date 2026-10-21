/**
 * Card imagery from existing Cardyssey assets. `src`, `name` and `type` refer to authentic
 * Pokémon TCG assets – every card visual on the page reads from this list.
 */
export type CollectorCard = {
  id: string
  name: string
  type: string
  src: string
}

export const cards: CollectorCard[] = [
  { id: 'water', name: 'Glurak', type: 'Feuer', src: '/landing/cards/base1-4.png' },
  { id: 'grass', name: 'Pokémon TCG', type: 'Sammelkarte', src: '/landing/cards/sv3-223.png' },
  { id: 'fire', name: 'Pokémon TCG', type: 'Sammelkarte', src: '/landing/cards/sv4-234.png' },
  { id: 'electric', name: 'Pokémon TCG', type: 'Sammelkarte', src: '/landing/cards/swsh12pt5-160.png' },
  { id: 'psychic', name: 'Dark Magician', type: 'Yu-Gi-Oh!', src: '/landing/cards/yugioh-dark-magician.jpg' },
]

export function cardAlt(card: CollectorCard) {
  return `Sammelkarte ${card.name}, Typ ${card.type}`
}
