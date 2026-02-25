from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    MQTT_BROKER_HOST: str
    MQTT_BROKER_PORT: int
    MQTT_USERNAME: str
    MQTT_PASSWORD: str
    MQTT_CLIENT_ID: str
    MQTT_TOPIC_READINGS: str
    MQTT_TOPIC_VALVE: str

    INSERT_BATCH_SIZE: int = 50
    INSERT_BATCH_FLUSH_SECONDS: int = 5

    class Config:
        env_file = ".env"

settings = Settings()