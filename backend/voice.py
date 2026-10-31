from twilio.twiml.voice_response import VoiceResponse, Gather


def create_incoming_voice_response(action_url):
    response = VoiceResponse()

    gather = Gather(
        input="speech",
        action=action_url,
        method="POST",
        speech_timeout="auto",
        language="en-IN"
    )

    gather.say(
        "Welcome to Support IQ. Please describe your issue after the beep.",
        language="en-IN"
    )

    response.append(gather)
    response.say(
        "We could not hear your response. Please call again.",
        language="en-IN"
    )
    response.hangup()

    return str(response)


def create_voice_reply(message):
    response = VoiceResponse()
    response.say(message, language="en-IN")
    response.hangup()
    return str(response)
