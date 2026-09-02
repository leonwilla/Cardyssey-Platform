<?php get_header(); ?>

<main class="section">
    <div class="container">

        <?php if (have_posts()) : ?>

            <?php while (have_posts()) : the_post(); ?>
                <article>
                    <h1><?php the_title(); ?></h1>
                    <?php the_content(); ?>
                </article>
            <?php endwhile; ?>

        <?php else : ?>
            <p>Keine Inhalte gefunden.</p>
        <?php endif; ?>

    </div>
</main>

<?php get_footer(); ?>
