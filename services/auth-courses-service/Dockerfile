FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY src/AuthCourses.Api/AuthCourses.Api.csproj src/AuthCourses.Api/
RUN dotnet restore src/AuthCourses.Api/AuthCourses.Api.csproj

COPY src/ src/
RUN dotnet publish src/AuthCourses.Api/AuthCourses.Api.csproj \
    -c Release \
    -o /app/publish \
    --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /app/publish .

ENV ASPNETCORE_URLS=http://+:5001
EXPOSE 5001
ENTRYPOINT ["dotnet", "AuthCourses.Api.dll"]
