FROM mcr.microsoft.com/dotnet/sdk:8.0
WORKDIR /app
COPY . .
RUN dotnet restore || true
ENTRYPOINT ["dotnet", "run"]
