FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY src/MoodleSync.Api/MoodleSync.Api.csproj src/MoodleSync.Api/
RUN dotnet restore src/MoodleSync.Api/MoodleSync.Api.csproj

COPY src/ src/
RUN dotnet publish src/MoodleSync.Api/MoodleSync.Api.csproj \
    -c Release \
    -o /app/publish \
    --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /app/publish .

ENV ASPNETCORE_URLS=http://+:5002
EXPOSE 5002
ENTRYPOINT ["dotnet", "MoodleSync.Api.dll"]
