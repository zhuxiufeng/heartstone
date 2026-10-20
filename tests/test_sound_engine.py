from core.sound_engine import SoundEngine, generate_tone_wav


def test_generate_tone_wav():
    wav_bytes = generate_tone_wav([440.0], duration_sec=0.05)
    assert wav_bytes.startswith(b"RIFF")
    assert b"WAVE" in wav_bytes


def test_sound_engine_singleton_and_notifications():
    engine = SoundEngine.get_instance()
    assert engine is not None
    engine.update_settings(sound_enabled=False, tts_enabled=False)

    # Should execute without errors
    engine.notify_lethal(damage=15)
    engine.notify_aoe_threat("烈焰风暴")
    engine.notify_coin_opportunity()
    engine.notify_card_picked("火球术")
