#!/usr/bin/env bash
# Live Audio Stream Service Script

# --------------------------------------------
# 21 Aug 2026  Steve Davis
# Mod to keep audio detection enabled whenever
#  Spectrogram page is displayed.
# Mod to switch betweem Mic or WAV file input.
# =============================================

source /etc/birdnet/birdnet.conf

# Read the logging level from the configuration option
LOGGING_LEVEL="${LogLevel_LiveAudioStreamService}"
# If empty for some reason default to log level of error
[ -z "$LOGGING_LEVEL" ] && LOGGING_LEVEL="error"
# Additionally if we're at debug or info level then allow printing of script commands and variables
if [ "$LOGGING_LEVEL" == "info" ] || [ "$LOGGING_LEVEL" == "debug" ];then
  # Enable printing of commands/variables etc to terminal for debugging
  set -x
fi

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# ultrasonic envelope extraction: provide means to 'hear' bat calls, by converting 20-60kHz
# 'Squared Envelope' method
FREQSHIFT_OPT='highpass=f=20000,lowpass=f=60000,aeval=val(0)*val(0),lowpass=f=1000,aeval=sqrt(val(0)),volume=10'

#-------------------------------------------------------------------------------------------

if [ -z "${REC_CARD}" ];then
  echo "Stream not supported"
elif [[ -n "${RTSP_STREAM}" ]];then
  # Explode the RSPT steam setting into an array so we can count the number we have
  RSTP_STREAMS_EXPLODED_ARRAY=("${RTSP_STREAM//,/ }")

  # If for some reason the RTSP_STREAM_TO_LIVESTREAM is not set, then init it to 0 to use the first stream
  if [[ -z "${RTSP_STREAM_TO_LIVESTREAM}" ]];then
    RTSP_STREAM_TO_LIVESTREAM=0
  fi

  # Get the RSTP stream at the specified array index
  SELECTED_RSTP_STREAM="${RSTP_STREAMS_EXPLODED_ARRAY[RTSP_STREAM_TO_LIVESTREAM]}"

  # If for some reason the RTSP stream url is null
  if [[ -z "${SELECTED_RSTP_STREAM}" ]];then
    # Try select the first stream
    SELECTED_RSTP_STREAM="${RSTP_STREAMS_EXPLODED_ARRAY[0]}"
  fi

  ffmpeg -nostdin -loglevel "$LOGGING_LEVEL" -ac "${CHANNELS}" -i "${SELECTED_RSTP_STREAM}" -acodec libmp3lame \
    -b:a 320k -ac "${CHANNELS}" -content_type 'audio/mpeg' \
    -af "${FREQSHIFT_OPT}" \
    -f mp3 icecast://source:"${ICE_PWD}"@localhost:8000/stream -re
    
else
    if [ "$TEST_FILE_AS_INPUT" == "true" ]; then
      # Replace microphone with WAV file
        ffmpeg -nostdin -loglevel "$LOGGING_LEVEL" \
          -re -stream_loop -1 \
          -i /home/steve/BirdNET-Pi/tests/bat-test.wav \
          -acodec libmp3lame \
          -b:a 320k -ac "${CHANNELS}" -content_type 'audio/mpeg' \
          -af "${FREQSHIFT_OPT}" \
          -f mp3 icecast://source:"${ICE_PWD}"@localhost:8000/stream -re
    else
      # run with microphone
	    ffmpeg -nostdin -loglevel "$LOGGING_LEVEL" -ac "${CHANNELS}" -f alsa -i "${REC_CARD}" -acodec libmp3lame \
          -b:a 320k -ac "${CHANNELS}" -content_type 'audio/mpeg' \
          -af "${FREQSHIFT_OPT}" \
          -f mp3 icecast://source:"${ICE_PWD}"@localhost:8000/stream -re
    fi
fi
