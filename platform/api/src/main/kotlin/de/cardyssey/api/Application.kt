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
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import org.flywaydb.core.Flyway

@Serializable
data class HealthResponse(
    val status: String,
    val database: String,
    val service: String,
    val version: String
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

    val collectionRepository =
        CollectionRepository(database)

    val friendshipRepository =
        FriendshipRepository(database)

    val privacyRepository =
        PrivacyRepository(database)

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

    val cardCatalog =
        CardCatalogService(
            catalogCache
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
                        "0.2.0"
                )
            )
        }

        authRoutes(
            authRepository,
            tokenService
        )

        collectionRoutes(
            collectionRepository
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

        showcaseRoutes(
            showcaseRepository,
            privacyRepository
        )

        wishlistRoutes(
            wishlistRepository
        )

        sellingRoutes(
            sellingRepository
        )

        marketplaceRoutes(
            sellingRepository
        )

        marketplaceOfferRoutes(
            marketplaceOfferRepository
        )

        cardCatalogRoutes(
            cardCatalog
        )

        cardRecognitionRoutes(
            cardCatalog
        )

        setCatalogRoutes(
            cardCatalog
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
