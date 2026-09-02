FROM gradle:8.13-jdk21 AS build

WORKDIR /app

COPY settings.gradle.kts .
COPY build.gradle.kts .
COPY src ./src

RUN gradle installDist \
    --no-daemon


FROM eclipse-temurin:21-jre

WORKDIR /app

RUN useradd \
    --system \
    --uid 10001 \
    --create-home \
    cardyssey

COPY --from=build \
    /app/build/install/cardyssey-api \
    /app

USER cardyssey

EXPOSE 8080

ENTRYPOINT ["/app/bin/cardyssey-api"]
