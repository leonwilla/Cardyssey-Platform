<?php get_header(); ?>

<main>

    <section class="hero">
        <div class="container hero-grid">

            <div>
                <span class="eyebrow">Trading Cards · Collectibles · Culture</span>

                <h1>
                    Deine Reise durch
                    <span class="gradient-text">die Welt der Karten.</span>
                </h1>

                <p class="hero-copy">
                    Entdecke Trading Cards, Collectibles und ausgewählte Pieces.
                    Baue deine Sammlung auf und verwalte sie später direkt mit unserer App.
                </p>

                <div class="button-row">
                    <a class="btn btn-primary" href="<?php echo esc_url(cardyssey_shop_url()); ?>">
                        Shop entdecken
                    </a>

                    <a class="btn btn-secondary" href="#app">
                        App entdecken
                    </a>
                </div>
            </div>

            <div class="hero-visual">
                <div class="hero-world"></div>
                <div class="hero-card one"></div>
                <div class="hero-card two"></div>
                <div class="hero-card three"></div>
            </div>

        </div>
    </section>


    <section id="tcg-worlds" class="section">
        <div class="container">

            <div class="section-heading">
                <div>
                    <span class="eyebrow">Explore</span>
                    <h2>Entdecke deine TCG-Welt</h2>
                    <p>Von aktuellen Releases bis zu klassischen Sets.</p>
                </div>
            </div>

            <div class="world-grid">

                <a class="world-card" href="<?php echo esc_url(home_url('/product-category/pokemon/')); ?>">
                    <div class="world-icon">PK</div>
                    <div>
                        <strong>Pokémon</strong><br>
                        <span>Booster · Displays · Singles</span>
                    </div>
                </a>

                <a class="world-card" href="<?php echo esc_url(home_url('/product-category/one-piece/')); ?>">
                    <div class="world-icon">OP</div>
                    <div>
                        <strong>One Piece</strong><br>
                        <span>Sets · Displays · Collection</span>
                    </div>
                </a>

                <a class="world-card" href="<?php echo esc_url(home_url('/product-category/lorcana/')); ?>">
                    <div class="world-icon">LC</div>
                    <div>
                        <strong>Lorcana</strong><br>
                        <span>Booster · Sets · Zubehör</span>
                    </div>
                </a>

                <a class="world-card" href="<?php echo esc_url(home_url('/product-category/yugioh/')); ?>">
                    <div class="world-icon">YG</div>
                    <div>
                        <strong>Yu-Gi-Oh!</strong><br>
                        <span>Booster · Displays · Decks</span>
                    </div>
                </a>

                <a class="world-card" href="<?php echo esc_url(home_url('/product-category/magic/')); ?>">
                    <div class="world-icon">MTG</div>
                    <div>
                        <strong>Magic</strong><br>
                        <span>Sets · Booster · Commander</span>
                    </div>
                </a>

            </div>

        </div>
    </section>


    <section class="section product-zone">
        <div class="container">

            <div class="section-heading">
                <div>
                    <span class="eyebrow">New Drops</span>
                    <h2>Neu im Shop</h2>
                    <p>Frische Produkte und aktuelle Releases.</p>
                </div>

                <a class="btn btn-secondary" href="<?php echo esc_url(cardyssey_shop_url()); ?>">
                    Alle Produkte
                </a>
            </div>

            <?php
            if (class_exists('WooCommerce')) {
                echo do_shortcode('[products limit="8" columns="4" orderby="date" order="DESC"]');
            } else {
                echo '<div class="empty-products">WooCommerce wird geladen.</div>';
            }
            ?>

        </div>
    </section>


    <section id="app" class="section">
        <div class="container">

            <div class="feature-panel">
                <div class="app-grid">

                    <div>
                        <div class="phone">
                            <div class="phone-screen">
                                <span class="eyebrow">Scanner</span>
                                <div class="scan-frame"></div>
                            </div>
                        </div>
                    </div>

                    <div class="app-copy">
                        <span class="eyebrow">Card Collection App</span>

                        <h2>
                            Deine Sammlung.
                            <span class="gradient-text">Deine Reise.</span>
                        </h2>

                        <p class="hero-copy">
                            Karten scannen, Varianten erkennen, Marktwerte vergleichen
                            und komplette Sets über verschiedene TCGs hinweg vervollständigen.
                        </p>

                        <div class="features">

                            <div class="feature">
                                <span class="feature-bullet">✓</span>
                                Karten schnell per Scanner erfassen
                            </div>

                            <div class="feature">
                                <span class="feature-bullet">✓</span>
                                Sammlung und Varianten verwalten
                            </div>

                            <div class="feature">
                                <span class="feature-bullet">✓</span>
                                Marktpreise aus mehreren Quellen
                            </div>

                            <div class="feature">
                                <span class="feature-bullet">✓</span>
                                Sets und komplette Kartenwelten vervollständigen
                            </div>

                        </div>

                        <a class="btn btn-primary" href="#">
                            Bald verfügbar
                        </a>

                    </div>

                </div>
            </div>

        </div>
    </section>


    <section id="collectibles" class="section">
        <div class="container">

            <div class="section-heading">
                <div>
                    <span class="eyebrow">Beyond Cards</span>
                    <h2>Collectibles & mehr</h2>
                    <p>Ausgewählte Sammlerstücke neben unserem TCG-Kernsortiment.</p>
                </div>
            </div>

        </div>
    </section>


    <section id="fashion" class="section">
        <div class="container">

            <div class="section-heading">
                <div>
                    <span class="eyebrow">Selected Pieces</span>
                    <h2>Fashion</h2>
                    <p>Einzelstücke, besondere Pieces und wechselnde Drops.</p>
                </div>
            </div>

        </div>
    </section>

</main>

<?php get_footer(); ?>
