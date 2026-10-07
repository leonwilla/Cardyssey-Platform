// Auto-deploy backend test
package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpStatusCode
import io.ktor.serialization.kotlinx.json.json
import io.ktor.server.application.Application
import io.ktor.server.application.call
import io.ktor.server.application.install
import io.ktor.server.auth.Authentication
import io.ktor.server.auth.jwt.JWTPrincipal
import io.ktor.server.auth.jwt.jwt
import io.ktor.server.engine.embeddedServer
import io.ktor.server.netty.Netty
import io.ktor.server.plugins.calllogging.CallLogging
import io.ktor.server.plugins.contentnegotiation.ContentNegotiation
import io.ktor.server.plugins.cors.routing.CORS
import io.ktor.server.plugins.statuspages.StatusPages
import io.ktor.server.response.respond
import io.ktor.server.routing.get
import io.ktor.server.routing.routing
import kotlinx.coroutines.launch
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import org.flywaydb.core.Flyway
import java.nio.file.Path

@Serializable
data class HealthResponse(
    val status: String,
    val database: String,
    val service: String,
    val version: String,
    val justTcgConfigured: Boolean,
    val ebayPricingMode: String,
    val ebayDirectEnabled: Boolean,
    val ebayDirectSessionConfigured: Boolean,
    val ebayPriceCacheTtlHours: Long,
    val tcgPriceCacheTtlHours: Long,
    val tcgPriceWorkerEnabled: Boolean
)

fun main() {
    val port =
        System.getenv("PORT")
            ?.toIntOrNull()
            ?: 8080

    embeddedServer(
        factory = Netty,
        port = port,
        host = "0.0.0.0",
        module = Application::module
    ).start(wait = true)
}

fun Application.module() {

    val appLog = environment.log

    val database =
        createDataSource()

    migrateDatabase(database)

    val tokenService =
        TokenService(
            requireEnv("JWT_SECRET")
        )

    val authRepository =
        AuthRepository(database)

    val roleRepository =
        RoleRepository(database)

    val adminRepository =
        AdminRepository(database)

    val adminUserManagementRepository =
        AdminUserManagementRepository(database)

    val registrationSettingsRepository =
        RegistrationSettingsRepository(database)

    val collectionRepository =
        CollectionRepository(database)

    val friendshipRepository =
        FriendshipRepository(database)

    val privacyRepository =
        PrivacyRepository(database)

    val appearanceRepository =
        AppearanceRepository(database)

    val pushNotifications =
        PushNotificationService(
            database
        )

    val chatReactions =
        ChatReactionRepository(
            database
        )

    val chatRepository =
        ChatRepository(
            dataSource = database,
            friendships = friendshipRepository,
            push = pushNotifications,
            reactions = chatReactions
        )

    val chatModerationRepository =
        ChatModerationRepository(database)

    val groupChatRepository =
        GroupChatRepository(
            dataSource = database,
            friendships = friendshipRepository,
            push = pushNotifications,
            reactions = chatReactions
        )

    val communityChatRepository =
        CommunityChatRepository(
            dataSource = database,
            push = pushNotifications,
            reactions = chatReactions
        )

    val showcaseRepository =
        ShowcaseRepository(database)

    val friendCollectionRepository =
        FriendCollectionRepository(database)

    val friendSetRepository =
        FriendSetRepository(database)

    val wishlistRepository =
        WishlistRepository(database)

    val sellingRepository =
        SellingRepository(database)

    val marketplaceOfferRepository =
        MarketplaceOfferRepository(database)

    val catalogCache =
        CatalogCacheRepository(
            database
        )

    val ebayPriceCache =
        EbayPriceCacheRepository(
            database
        )

    val tcgPriceCache =
        TcgPriceCacheRepository(
            database
        )

    val publicApiUrl =
        System.getenv("PUBLIC_API_URL")
            ?.trim()
            ?.removeSuffix("/")
            ?.takeIf(String::isNotBlank)
            ?: "https://api.cardyssey.de"

    val catalogDir =
        Path.of(
            System.getenv("CATALOG_DIR")
                ?.trim()
                ?.takeIf(String::isNotBlank)
                ?: "/data/catalog"
        )

    val permanentCatalog =
        PermanentCatalogRepository(
            dataSource = database,
            catalogDir = catalogDir,
            publicBaseUrl = publicApiUrl
        )

    val supplementalCatalog = SupplementalCatalogRepository(database, permanentCatalog)
    val cardCatalog = CardCatalogService(catalogCache, supplementalCatalog, permanentCatalog)

    val catalogImageHasher =
        CatalogImageHasher()

    // Keep background work limited to the languages selectable in the Android app.
    val appCatalogLanguages = listOf("de", "en", "ko", "ja", "zh-tw", "zh-cn")
    val catalogLanguages = System.getenv("CATALOG_LANGUAGES")
        ?.split(",")?.map { it.trim().lowercase() }
        ?.filter { it in appCatalogLanguages }?.distinct()
        ?.takeIf { it.isNotEmpty() } ?: appCatalogLanguages

    val catalogSyncIntervalHours =
        System.getenv("CATALOG_SYNC_INTERVAL_HOURS")
            ?.toLongOrNull()
            ?.coerceAtLeast(1L)
            ?: 24L

    val catalogSync =
        CatalogMirrorSyncService(
            catalog = cardCatalog,
            mirror = permanentCatalog,
            images = catalogImageHasher,
            languages = catalogLanguages,
            syncIntervalHours =
                catalogSyncIntervalHours,
            detailBatchSize =
                System.getenv(
                    "CATALOG_DETAIL_BATCH_SIZE"
                )
                    ?.toIntOrNull()
                    ?.coerceIn(10, 2_000)
                    ?: 250,
            imageBatchSize =
                System.getenv(
                    "CATALOG_IMAGE_BATCH_SIZE"
                )
                    ?.toIntOrNull()
                    ?.coerceIn(10, 2_000)
                    ?: 250,
            imagesEnabled =
                System.getenv(
                    "CATALOG_DOWNLOAD_IMAGES"
                )
                    ?.toBooleanStrictOrNull()
                    ?: true
        )

    /*
     * Search traffic never waits for the first full import. Source refresh,
     * detail completion and image mirroring continue in the application
     * lifecycle and resume from PostgreSQL/files after every restart.
     */
    launch {
        catalogSync.runForever()
    }

    val justTcgApiKey =
        System.getenv("JUSTTCG_API_KEY")
            ?.trim()
            ?.takeIf(String::isNotBlank)

    val ebayDirectEnabled =
        System.getenv("EBAY_DIRECT_ENABLED")
            ?.trim()
            ?.toBooleanStrictOrNull()
            ?: true

    val ebayBrowserUrl =
        System.getenv("EBAY_BROWSER_URL")
            ?.trim()
            .orEmpty()

    /*
     * Der direkte Cardyssey-Collector darf die vorhandene ebay.de-Session
     * weiterverwenden. Der alte Secret-Name bleibt vorerst nur als
     * Deployment-Kompatibilität erhalten; SoldComps ist keine Preisquelle.
     */
    val legacyEbaySessionCookies =
        System.getenv("SOLDCOMPS_EBAY_COOKIES")
            ?.trim()
            .orEmpty()

    val ebayDirectCookies =
        System.getenv("EBAY_DIRECT_COOKIES")
            ?.trim()
            ?.takeIf(String::isNotBlank)
            ?: legacyEbaySessionCookies

    /*
     * Der eBay-Marktwert wird global pro Karte/Sprache/Variante geteilt.
     * Dadurch löst nicht jede Collection und nicht jeder Nutzer erneut einen
     * Provider-Request aus. Standard: sieben Tage bis zum nächsten Refresh.
     */
    val ebayPriceCacheTtlHours =
        System.getenv("EBAY_PRICE_CACHE_TTL_HOURS")
            ?.toLongOrNull()
            ?.takeIf { it > 0L }
            ?: 168L

    val liveCardPricing =
        CardPricingService(
            catalog = cardCatalog,
            justTcgApiKey =
                justTcgApiKey
        )

    val tcgPriceCacheTtlHours =
        System.getenv(
            "TCG_PRICE_CACHE_TTL_HOURS"
        )
            ?.toLongOrNull()
            ?.takeIf {
                it > 0L
            }
            ?: 168L

    val tcgPriceWorkerEnabled =
        System.getenv(
            "TCG_PRICE_WORKER_ENABLED"
        )
            ?.toBooleanStrictOrNull()
            ?: true

    val tcgPricing =
        CachedTcgPricingService(
            catalog =
                cardCatalog,
            cache =
                tcgPriceCache,
            livePricing =
                liveCardPricing,
            languages =
                catalogLanguages,
            cacheTtlHours =
                tcgPriceCacheTtlHours,
            batchSize =
                System.getenv(
                    "TCG_PRICE_WORKER_BATCH_SIZE"
                )
                    ?.toIntOrNull()
                    ?.coerceIn(
                        1,
                        2_000
                    )
                    ?: 100,
            requestSpacingMs =
                System.getenv(
                    "TCG_PRICE_REQUEST_SPACING_MS"
                )
                    ?.toLongOrNull()
                    ?.coerceAtLeast(
                        100L
                    )
                    ?: 250L,
            justTcgFallbacksPerDay =
                System.getenv(
                    "JUSTTCG_FALLBACKS_PER_DAY"
                )
                    ?.toIntOrNull()
                    ?.coerceAtLeast(
                        0
                    )
                    ?: 80,
            missingRetryHours =
                System.getenv(
                    "TCG_PRICE_MISSING_RETRY_HOURS"
                )
                    ?.toLongOrNull()
                    ?.coerceAtLeast(
                        1L
                    )
                    ?: 168L,
            providerErrorRetryHours =
                System.getenv(
                    "TCG_PRICE_ERROR_RETRY_HOURS"
                )
                    ?.toLongOrNull()
                    ?.coerceAtLeast(
                        1L
                    )
                    ?: 6L
        )

    if (tcgPriceWorkerEnabled) {
        launch {
            tcgPricing.runForever()
        }
    }

    val ebayProviders =
        buildList<EbayQuoteProvider> {
            if (ebayDirectEnabled) {
                add(
                    CompSniperEbayQuoteProvider(
                        catalog = cardCatalog,
                        /*
                         * Absichtlich leer: Schlägt unser direkter Collector
                         * fehl, wird kein externer Anbieter als Fallback
                         * aufgerufen.
                         */
                        apiKey = "",
                        directCollector =
                            EbayDirectSoldListingCollector(
                                cookieHeader =
                                    ebayDirectCookies,
                                requestSpacingMs =
                                    if (ebayBrowserUrl.isBlank()) {
                                        2_000L
                                    } else {
                                        15_000L
                                    },
                                browserPageLoader =
                                    ebayBrowserUrl
                                        .takeIf(String::isNotBlank)
                                        ?.let(
                                            ::EbayBrowserPageLoader
                                        )
                            )
                    )
                )
            }
        }

    val ebayPricing =
        CachedEbayPricingService(
            catalog = cardCatalog,
            cache = ebayPriceCache,
            providers = ebayProviders,
            cacheTtlMs =
                ebayPriceCacheTtlHours * 60L * 60L * 1000L
        )

    install(CallLogging)

    install(ContentNegotiation) {
        json(
            Json {
                prettyPrint = false
                ignoreUnknownKeys = true
                encodeDefaults = true
            }
        )
    }

    install(CORS) {
        allowHost(
            "localhost:3000",
            schemes = listOf("http")
        )

        allowHost(
            "127.0.0.1:3000",
            schemes = listOf("http")
        )

        allowHeader(
            HttpHeaders.ContentType
        )

        allowHeader(
            HttpHeaders.Authorization
        )

        allowCredentials = true
    }

    install(Authentication) {
        jwt("auth-jwt") {

            realm = "cardyssey"

            verifier(
                tokenService.verifier
            )

            validate { credential ->
                val subject =
                    credential.payload.subject

                if (
                    subject != null &&
                    runCatching {
                        java.util.UUID.fromString(
                            subject
                        )
                    }.isSuccess
                ) {
                    JWTPrincipal(
                        credential.payload
                    )
                } else {
                    null
                }
            }
        }
    }

    install(StatusPages) {
        exception<Throwable> {
                call,
                cause ->

            appLog.error(
                "Unhandled API error",
                cause
            )

            call.respond(
                HttpStatusCode.InternalServerError,
                mapOf(
                    "error" to
                        "internal_server_error"
                )
            )
        }
    }

    routing {

        get("/") {
            call.respond(
                mapOf(
                    "service" to
                        "Cardyssey API",
                    "status" to
                        "online"
                )
            )
        }

        get("/api/v1/health") {

            val dbHealthy =
                runCatching {
                    database.connection.use {
                            connection ->

                        connection
                            .prepareStatement(
                                "SELECT 1"
                            )
                            .use {
                                    statement ->

                                statement
                                    .executeQuery()
                                    .use {
                                            result ->

                                        result.next()
                                    }
                            }
                    }
                }.getOrDefault(false)

            call.respond(
                if (dbHealthy) {
                    HttpStatusCode.OK
                } else {
                    HttpStatusCode.ServiceUnavailable
                },

                HealthResponse(
                    status =
                        if (dbHealthy) {
                            "ok"
                        } else {
                            "degraded"
                        },

                    database =
                        if (dbHealthy) {
                            "connected"
                        } else {
                            "unavailable"
                        },

                    service =
                        "cardyssey-api",

                    version =
                        "0.3.0",

                    justTcgConfigured =
                        justTcgApiKey != null,

                    ebayPricingMode =
                        "CARDYSSEY_DIRECT_ONLY",

                    ebayDirectEnabled =
                        ebayDirectEnabled,

                    ebayDirectSessionConfigured =
                        ebayDirectCookies.isNotBlank(),

                    ebayPriceCacheTtlHours =
                        ebayPriceCacheTtlHours,

                    tcgPriceCacheTtlHours =
                        tcgPriceCacheTtlHours,

                    tcgPriceWorkerEnabled =
                        tcgPriceWorkerEnabled
                )
            )
        }

        authRoutes(
            repository = authRepository,
            tokens = tokenService,
            registrationSettings =
                registrationSettingsRepository
        )

        avatarRoutes(
            authRepository
        )

        adminRoutes(
            roles = roleRepository,
            admin = adminRepository,
            userManagement =
                adminUserManagementRepository,
            registrationSettings =
                registrationSettingsRepository,
            justTcgConfigured =
                justTcgApiKey != null,
            soldCompsConfigured =
                false
        )

        collectionRoutes(
            repository =
                collectionRepository,
            tcgPriceCache =
                tcgPriceCache
        )

        friendshipRoutes(
            friendshipRepository,
            privacyRepository,
            showcaseRepository,
            friendCollectionRepository,
            friendSetRepository,
            wishlistRepository
        )

        privacyRoutes(
            privacyRepository
        )

        appearanceRoutes(
            appearanceRepository
        )

        pushNotificationRoutes(
            pushNotifications
        )

        chatRoutes(
            chatRepository
        )

        groupChatRoutes(
            groupChatRepository
        )

        communityChatRoutes(
            repository = communityChatRepository,
            roles = roleRepository
        )

        chatModerationRoutes(
            repository = chatModerationRepository,
            roles = roleRepository
        )

        showcaseRoutes(
            showcaseRepository,
            privacyRepository
        )

        wishlistRoutes(
            wishlistRepository
        )

        sellingRoutes(
            repository =
                sellingRepository,
            push =
                pushNotifications
        )

        marketplaceRoutes(
            sellingRepository
        )

        marketplaceOfferRoutes(
            repository =
                marketplaceOfferRepository,
            push =
                pushNotifications
        )

        cardCatalogRoutes(
            catalog = cardCatalog,
            mirror = permanentCatalog
        )

        cardRecognitionRoutes(
            catalog = cardCatalog,
            mirror = permanentCatalog,
            imageHasher = catalogImageHasher
        )

        setCatalogRoutes(
            cardCatalog
        )

        pricingRoutes(
            catalog = cardCatalog,
            pricing = tcgPricing,
            ebayPricing = ebayPricing
        )
    }
}

private fun migrateDatabase(
    dataSource: HikariDataSource
) {
    Flyway
        .configure()
        .dataSource(dataSource)
        .locations(
            "classpath:db/migration"
        )
        .load()
        .migrate()
}

