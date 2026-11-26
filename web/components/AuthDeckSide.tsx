/** Linke Seite der Anmeldung im Kartendeck-Look: Spieltisch mit Kartenfächer. */
export function AuthDeckSide() {
  return (
    <aside className="authDeckSide" aria-hidden="true">
      <div className="authDeckInner">
        <span className="authDeckEyebrow">Cardyssey · Sammelkarten</span>
        <h2 className="authDeckTitle">Deine Sammlung.<br /><span>Dein Deck.</span></h2>
        <p className="authDeckText">Scannen, sammeln und den Wert mit echten Cardmarket-Preisen verfolgen – in der App und im Browser.</p>
        <div className="authDeckFan">
          <img src="/landing/cards/sv3-223.png" alt="" />
          <img src="/landing/cards/base1-4.png" alt="" />
          <img src="/landing/cards/sv4-234.png" alt="" />
        </div>
        <ul className="authDeckList">
          <li>Scanner für Pokémon-Karten</li>
          <li>Cardmarket-Preise alle 2 Stunden</li>
          <li>Sets, Wunschliste und Freunde</li>
        </ul>
      </div>
    </aside>
  );
}
