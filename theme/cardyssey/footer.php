<footer class="site-footer">
    <div class="container">

        <div class="footer-grid">

            <div>
                <a class="brand" href="<?php echo esc_url(home_url('/')); ?>">
                    <span class="brand-mark">
                        <span class="brand-card"></span>
                        <span class="brand-card"></span>
                        <span class="brand-orbit"></span>
                    </span>
                    <span>CARDYSSEY</span>
                </a>

                <p style="color:var(--muted);max-width:330px;margin-top:18px;">
                    Trading Cards, Collectibles und ausgewählte Pieces.
                    Entdecken. Sammeln. Tauschen.
                </p>
            </div>

            <div>
                <div class="footer-title">Shop</div>
                <div class="footer-links">
                    <a href="<?php echo esc_url(cardyssey_shop_url()); ?>">Alle Produkte</a>
                    <a href="#tcg-worlds">Trading Cards</a>
                    <a href="#collectibles">Collectibles</a>
                    <a href="#fashion">Fashion</a>
                </div>
            </div>

            <div>
                <div class="footer-title">Cardyssey</div>
                <div class="footer-links">
                    <a href="#app">App</a>
                    <a href="#">Über uns</a>
                    <a href="#">Kontakt</a>
                </div>
            </div>

            <div>
                <div class="footer-title">Service</div>
                <div class="footer-links">
                    <a href="#">Versand</a>
                    <a href="#">FAQ</a>
                    <a href="#">Impressum</a>
                    <a href="#">Datenschutz</a>
                </div>
            </div>

        </div>

        <div class="footer-bottom">
            © <?php echo date('Y'); ?> Cardyssey · Aktueller Entwicklungsstand
        </div>

    </div>
</footer>

<?php wp_footer(); ?>
</body>
</html>
