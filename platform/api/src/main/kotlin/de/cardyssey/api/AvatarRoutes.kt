package de.cardyssey.api

import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.response.respondFile
import io.ktor.server.routing.Route
import io.ktor.server.routing.delete
import io.ktor.server.routing.get
import io.ktor.server.routing.put
import java.awt.RenderingHints
import java.awt.image.BufferedImage
import java.io.ByteArrayInputStream
import java.io.File
import java.util.UUID
import javax.imageio.ImageIO
import kotlin.math.max

private const val MAX_AVATAR_BYTES =
    5 * 1024 * 1024

private const val AVATAR_SIZE =
    512


fun avatarUrlFor(
    avatarPath: String?
): String? {

    if (avatarPath.isNullOrBlank()) {
        return null
    }

    val base =
        System.getenv(
            "PUBLIC_API_URL"
        )
            ?.trim()
            ?.removeSuffix("/")
            ?.takeIf {
                it.isNotBlank()
            }

    val path =
        "/api/v1/avatars/$avatarPath"

    return if (base == null) {
        path
    } else {
        "$base$path"
    }
}


private class AvatarStorage {

    private val directory =
        File(
            System.getenv(
                "AVATAR_DIR"
            )
                ?.takeIf {
                    it.isNotBlank()
                }
                ?: "/data/avatars"
        )

    init {
        directory.mkdirs()
    }


    fun save(
        userId: UUID,
        bytes: ByteArray
    ): String {

        require(
            bytes.isNotEmpty()
        ) {
            "empty_avatar"
        }

        require(
            bytes.size <=
                MAX_AVATAR_BYTES
        ) {
            "avatar_too_large"
        }

        val source =
            ImageIO.read(
                ByteArrayInputStream(
                    bytes
                )
            )
                ?: error(
                    "invalid_avatar_image"
                )

        require(
            source.width > 0 &&
                source.height > 0 &&
                source.width <= 12000 &&
                source.height <= 12000
        ) {
            "invalid_avatar_dimensions"
        }

        /*
         * Quadratisch zuschneiden und auf
         * 512x512 normalisieren.
         * Re-Encoding entfernt gleichzeitig
         * unnötige Bild-Metadaten.
         */
        val target =
            BufferedImage(
                AVATAR_SIZE,
                AVATAR_SIZE,
                BufferedImage.TYPE_INT_RGB
            )

        val graphics =
            target.createGraphics()

        try {
            graphics.setRenderingHint(
                RenderingHints.KEY_INTERPOLATION,
                RenderingHints.VALUE_INTERPOLATION_BICUBIC
            )

            graphics.setRenderingHint(
                RenderingHints.KEY_RENDERING,
                RenderingHints.VALUE_RENDER_QUALITY
            )

            val scale =
                max(
                    AVATAR_SIZE.toDouble() /
                        source.width.toDouble(),

                    AVATAR_SIZE.toDouble() /
                        source.height.toDouble()
                )

            val width =
                (
                    source.width *
                        scale
                ).toInt()

            val height =
                (
                    source.height *
                        scale
                ).toInt()

            val x =
                (
                    AVATAR_SIZE -
                        width
                ) / 2

            val y =
                (
                    AVATAR_SIZE -
                        height
                ) / 2

            graphics.drawImage(
                source,
                x,
                y,
                width,
                height,
                null
            )

        } finally {
            graphics.dispose()
        }

        val fileName =
            "${userId}_${UUID.randomUUID()}.jpg"

        val targetFile =
            File(
                directory,
                fileName
            )

        val written =
            ImageIO.write(
                target,
                "jpg",
                targetFile
            )

        check(written) {
            "avatar_encode_failed"
        }

        return fileName
    }


    fun delete(
        avatarPath: String?
    ) {
        if (
            avatarPath.isNullOrBlank()
        ) {
            return
        }

        if (
            !avatarPath.matches(
                Regex(
                    "^[A-Za-z0-9._-]+$"
                )
            )
        ) {
            return
        }

        File(
            directory,
            avatarPath
        ).delete()
    }


    fun resolvePublic(
        fileName: String
    ): File? {

        if (
            !fileName.matches(
                Regex(
                    "^[A-Za-z0-9._-]+\\.jpg$"
                )
            )
        ) {
            return null
        }

        val file =
            File(
                directory,
                fileName
            )

        return file.takeIf {
            it.isFile
        }
    }
}


fun Route.avatarRoutes(
    repository: AuthRepository
) {

    val storage =
        AvatarStorage()


    /*
     * Öffentliche Bildauslieferung.
     * Nur streng validierte Dateinamen.
     */
    get(
        "/api/v1/avatars/{fileName}"
    ) {

        val fileName =
            call.parameters[
                "fileName"
            ]

        val file =
            fileName
                ?.let {
                    storage.resolvePublic(
                        it
                    )
                }

        if (file == null) {
            call.respond(
                HttpStatusCode.NotFound
            )
            return@get
        }

        call.respondFile(
            file
        )
    }


    authenticate(
        "auth-jwt"
    ) {

        put(
            "/api/v1/me/avatar"
        ) {

            val id =
                call.authenticatedUserId()

            if (id == null) {
                call.respond(
                    HttpStatusCode.Unauthorized
                )
                return@put
            }

            val current =
                repository.findById(
                    id
                )

            if (current == null) {
                call.respond(
                    HttpStatusCode.NotFound
                )
                return@put
            }

            val bytes =
                call.receive<ByteArray>()

            if (
                bytes.isEmpty() ||
                bytes.size >
                    MAX_AVATAR_BYTES
            ) {
                call.respond(
                    HttpStatusCode.BadRequest,
                    mapOf(
                        "error" to
                            "invalid_avatar_size"
                    )
                )
                return@put
            }

            val newPath =
                runCatching {
                    storage.save(
                        id,
                        bytes
                    )
                }.getOrElse {

                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf(
                            "error" to
                                (
                                    it.message
                                        ?: "invalid_avatar"
                                )
                        )
                    )

                    return@put
                }


            val updated =
                repository
                    .updateAvatarPath(
                        id,
                        newPath
                    )

            if (updated == null) {

                storage.delete(
                    newPath
                )

                call.respond(
                    HttpStatusCode.NotFound
                )

                return@put
            }

            /*
             * Erst nach erfolgreichem DB-Write
             * das alte Bild entfernen.
             */
            storage.delete(
                current.avatarPath
            )

            call.respond(
                UserResponse(
                    id =
                        updated.id.toString(),
                    email =
                        updated.email,
                    displayName =
                        updated.displayName,
                    avatarUrl =
                        avatarUrlFor(
                            updated.avatarPath
                        )
                )
            )
        }


        delete(
            "/api/v1/me/avatar"
        ) {

            val id =
                call.authenticatedUserId()

            if (id == null) {
                call.respond(
                    HttpStatusCode.Unauthorized
                )
                return@delete
            }

            val current =
                repository.findById(
                    id
                )

            if (current == null) {
                call.respond(
                    HttpStatusCode.NotFound
                )
                return@delete
            }

            val updated =
                repository
                    .updateAvatarPath(
                        id,
                        null
                    )

            if (updated == null) {
                call.respond(
                    HttpStatusCode.NotFound
                )
                return@delete
            }

            storage.delete(
                current.avatarPath
            )

            call.respond(
                UserResponse(
                    id =
                        updated.id.toString(),
                    email =
                        updated.email,
                    displayName =
                        updated.displayName,
                    avatarUrl =
                        null
                )
            )
        }
    }
}
