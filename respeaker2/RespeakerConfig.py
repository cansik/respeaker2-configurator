# RespeakerConfig.py

import duit.ui as ui
from duit.model.DataField import DataField

from respeaker2.RespeakerParam import RespeakerParam


class RespeakerConfig:
    def __init__(self):


        # Adaptive Echo Canceler updates inhibit (0=adaptation on, 1=freeze)
        self.aec_freeze_on_off = (
                DataField(0)
                | ui.Boolean("AEC Freeze Adaptation",
                             tooltip="Adaptive Echo Canceler updates inhibit: 0=adaptation enabled, 1=freeze adaptation")
                | RespeakerParam(18, 7, 'int', 1, 0, 'rw')
        )

        # Limit on norm of AEC filter coefficients
        self.aec_norm = (
                DataField(0.25)
                | ui.Slider("AEC Norm", limit_min=0.25, limit_max=16.0,
                            tooltip="Limit on norm of AEC filter coefficients")
                | RespeakerParam(18, 19, 'float', 16.0, 0.25, 'rw')
        )

        # AEC Path Change Detection (read-only)
        self.aec_path_change = (
                DataField(0)
                | ui.Boolean("AEC Path Change", readonly=True,
                             tooltip="AEC Path Change Detection: 0=no change, 1=change detected")
                | RespeakerParam(18, 25, 'int', 1, 0, 'ro')
        )

        # Current RT60 estimate in seconds (read-only)
        self.rt60 = (
                DataField(0.25)
                | ui.Number("RT60 (s)", readonly=True, tooltip="Current RT60 estimate in seconds")
                | RespeakerParam(18, 26, 'float', 0.9, 0.25, 'ro')
        )

        # High-pass filter mode on mic signals (0=off,1=70Hz,2=125Hz,3=180Hz)
        self.hpf_on_off = (
                DataField(0)
                | ui.Options("HPF Mode", [0, 1, 2, 3],
                             tooltip="High-pass filter on mic signals: 0=off,1=70Hz,2=125Hz,3=180Hz")
                | RespeakerParam(18, 27, 'int', 3, 0, 'rw')
        )

        # RT60 estimation on/off
        self.rt60_on_off = (
                DataField(0)
                | ui.Boolean("RT60 Estimation", tooltip="RT60 estimation for AES: 0=off, 1=on")
                | RespeakerParam(18, 28, 'int', 1, 0, 'rw')
        )

        # Threshold for signal detection in AEC [-inf..0] dBov
        self.aec_silence_level = (
                DataField(1e-9)
                | ui.Slider("AEC Silence Level", limit_min=1e-9, limit_max=1.0,
                            tooltip="Threshold for signal detection in AEC [-inf..0] dBov")
                | RespeakerParam(18, 30, 'float', 1.0, 1e-9, 'rw')
        )

        # AEC far-end silence detection status (read-only)
        self.aec_silence_mode = (
                DataField(0)
                | ui.Boolean("AEC Far-end Silence", readonly=True,
                             tooltip="AEC far-end silence detection status: 0=signal, 1=silence")
                | RespeakerParam(18, 31, 'int', 1, 0, 'ro')
        )

        # Automatic Gain Control on/off
        self.agc_on_off = (
                DataField(0)
                | ui.Boolean("AGC On/Off", tooltip="Automatic Gain Control: 0=off, 1=on")
                | RespeakerParam(19, 0, 'int', 1, 0, 'rw')
        )

        # Maximum AGC gain factor [0..60] dB
        self.agc_max_gain = (
                DataField(1.0)
                | ui.Slider("AGC Max Gain (dB)", limit_min=1.0, limit_max=1000.0,
                            tooltip="Maximum AGC gain factor [0..60] dB")
                | RespeakerParam(19, 1, 'float', 1000.0, 1.0, 'rw')
        )

        # Target power level of the output signal [-inf..0] dBov
        self.agc_desired_level = (
                DataField(1e-8)
                | ui.Slider("AGC Desired Level", limit_min=1e-8, limit_max=0.99,
                            tooltip="Target power level of output signal [-inf..0] dBov")
                | RespeakerParam(19, 2, 'float', 0.99, 1e-8, 'rw')
        )

        # Current AGC gain factor [0..60] dB
        self.agc_gain = (
                DataField(1.0)
                | ui.Slider("AGC Gain (dB)", limit_min=1.0, limit_max=1000.0,
                            tooltip="Current AGC gain factor [0..60] dB")
                | RespeakerParam(19, 3, 'float', 1000.0, 1.0, 'rw')
        )

        # AGC time-constant in seconds
        self.agc_time_constant = (
                DataField(0.1)
                | ui.Slider("AGC Time Constant (s)", limit_min=0.1, limit_max=1.0,
                            tooltip="Ramps-up/down time-constant in seconds")
                | RespeakerParam(19, 4, 'float', 1.0, 0.1, 'rw')
        )

        # Comfort Noise Insertion on/off
        self.cni_on_off = (
                DataField(0)
                | ui.Boolean("Comfort Noise Insertion", tooltip="Comfort Noise Insertion: 0=off, 1=on")
                | RespeakerParam(19, 5, 'int', 1, 0, 'rw')
        )

        # Adaptive beamformer updates freeze
        self.beamformer_freeze = (
                DataField(0)
                | ui.Boolean("Beamformer Freeze", tooltip="Adaptive beamformer updates: 0=enabled,1=freeze")
                | RespeakerParam(19, 6, 'int', 1, 0, 'rw')
        )

        # Stationary noise suppression on/off
        self.stat_noise_suppression = (
                DataField(0)
                | ui.Boolean("Stationary Noise Suppression", tooltip="Stationary noise suppression: 0=off,1=on")
                | RespeakerParam(19, 8, 'int', 1, 0, 'rw')
        )

        # Over-subtraction factor of stationary noise
        self.gamma_ns = (
                DataField(0.0)
                | ui.Slider("Gamma NS", limit_min=0.0, limit_max=3.0,
                            tooltip="Over-subtraction factor of stationary noise")
                | RespeakerParam(19, 9, 'float', 3.0, 0.0, 'rw')
        )

        # Gain-floor for stationary noise suppression [-inf..0] dB
        self.limit_min_ns = (
                DataField(0.0)
                | ui.Slider("limit_min NS (dB)", limit_min=0.0, limit_max=1.0,
                            tooltip="Gain-floor for stationary noise suppression")
                | RespeakerParam(19, 10, 'float', 1.0, 0.0, 'rw')
        )

        # Non-stationary noise suppression on/off
        self.nonstat_noise_suppression = (
                DataField(0)
                | ui.Boolean("Non-stationary Noise Suppression", tooltip="Non-stationary noise suppression: 0=off,1=on")
                | RespeakerParam(19, 11, 'int', 1, 0, 'rw')
        )

        # Over-subtraction factor of non-stationary noise
        self.gamma_nn = (
                DataField(0.0)
                | ui.Slider("Gamma NN", limit_min=0.0, limit_max=3.0,
                            tooltip="Over-subtraction factor of non-stationary noise")
                | RespeakerParam(19, 12, 'float', 3.0, 0.0, 'rw')
        )

        # Gain-floor for non-stationary noise suppression [-inf..0] dB
        self.limit_min_nn = (
                DataField(0.0)
                | ui.Slider("limit_min NN (dB)", limit_min=0.0, limit_max=1.0,
                            tooltip="Gain-floor for non-stationary noise suppression")
                | RespeakerParam(19, 13, 'float', 1.0, 0.0, 'rw')
        )

        # Echo suppression on/off
        self.echo_suppression = (
                DataField(0)
                | ui.Boolean("Echo Suppression", tooltip="Echo suppression: 0=off,1=on")
                | RespeakerParam(19, 14, 'int', 1, 0, 'rw')
        )

        # Over-subtraction factor of echo (direct & early)
        self.gamma_e = (
                DataField(0.0)
                | ui.Slider("Gamma E", limit_min=0.0, limit_max=3.0,
                            tooltip="Over-subtraction factor of echo (direct & early)")
                | RespeakerParam(19, 15, 'float', 3.0, 0.0, 'rw')
        )

        # Over-subtraction factor of echo tail
        self.gamma_e_tail = (
                DataField(0.0)
                | ui.Slider("Gamma E Tail", limit_min=0.0, limit_max=3.0,
                            tooltip="Over-subtraction factor of echo tail")
                | RespeakerParam(19, 16, 'float', 3.0, 0.0, 'rw')
        )

        # Over-subtraction factor of non-linear echo
        self.gamma_enl = (
                DataField(0.0)
                | ui.Slider("Gamma ENL", limit_min=0.0, limit_max=5.0,
                            tooltip="Over-subtraction factor of non-linear echo")
                | RespeakerParam(19, 17, 'float', 5.0, 0.0, 'rw')
        )

        # Non-linear echo attenuation on/off
        self.nlatten_on_off = (
                DataField(0)
                | ui.Boolean("Non-linear Echo Attenuation", tooltip="Non-linear echo attenuation: 0=off,1=on")
                | RespeakerParam(19, 18, 'int', 1, 0, 'rw')
        )

        # Non-linear AEC training mode (0=off,1=phase1,2=phase2)
        self.nlaec_mode = (
                DataField(0)
                | ui.Options("NLAEC Mode", [0, 1, 2], tooltip="Non-linear AEC training mode: 0=off,1=phase1,2=phase2")
                | RespeakerParam(19, 20, 'int', 2, 0, 'rw')
        )

        # Speech detection status (read-only)
        self.speech_detected = (
                DataField(0)
                | ui.Boolean("Speech Detected", readonly=True, tooltip="Speech detection status: 0=no speech,1=speech")
                | RespeakerParam(19, 22, 'int', 1, 0, 'ro')
        )

        # FSB update decision (read-only)
        self.fsb_updated = (
                DataField(0)
                | ui.Boolean("FSB Updated", readonly=True, tooltip="FSB update decision: 0=not updated,1=updated")
                | RespeakerParam(19, 23, 'int', 1, 0, 'ro')
        )

        # FSB path change detection (read-only)
        self.fsb_path_change = (
                DataField(0)
                | ui.Boolean("FSB Path Change", readonly=True, tooltip="FSB path change detection: 0=no,1=yes")
                | RespeakerParam(19, 24, 'int', 1, 0, 'ro')
        )

        # Transient echo suppression on/off
        self.transient_echo = (
                DataField(0)
                | ui.Boolean("Transient Echo Suppression", tooltip="Transient echo suppression: 0=off,1=on")
                | RespeakerParam(19, 29, 'int', 1, 0, 'rw')
        )

        # Voice activity status (read-only)
        self.voice_activity = (
                DataField(0)
                | ui.Boolean("Voice Activity", readonly=True, tooltip="VAD voice activity status: 0=no,1=yes")
                | RespeakerParam(19, 32, 'int', 1, 0, 'ro')
        )

        # Stationary noise suppression for ASR on/off
        self.stat_noise_asr = (
                DataField(0)
                | ui.Boolean("Stationary Noise Suppression ASR",
                             tooltip="Stationary noise suppression for ASR: 0=off,1=on")
                | RespeakerParam(19, 33, 'int', 1, 0, 'rw')
        )

        # Non-stationary noise suppression for ASR on/off
        self.nonstat_noise_asr = (
                DataField(0)
                | ui.Boolean("Non-stationary Noise Suppression ASR",
                             tooltip="Non-stationary noise suppression for ASR: 0=off,1=on")
                | RespeakerParam(19, 34, 'int', 1, 0, 'rw')
        )

        # Over-subtraction factor NS for ASR
        self.gamma_ns_asr = (
                DataField(0.0)
                | ui.Slider("Gamma NS ASR", limit_min=0.0, limit_max=3.0,
                            tooltip="Over-subtraction factor of stationary noise for ASR")
                | RespeakerParam(19, 35, 'float', 3.0, 0.0, 'rw')
        )

        # Over-subtraction factor NN for ASR
        self.gamma_nn_asr = (
                DataField(0.0)
                | ui.Slider("Gamma NN ASR", limit_min=0.0, limit_max=3.0,
                            tooltip="Over-subtraction factor of non-stationary noise for ASR")
                | RespeakerParam(19, 36, 'float', 3.0, 0.0, 'rw')
        )

        # Gain-floor NS for ASR [-inf..0] dB
        self.limit_min_ns_asr = (
                DataField(0.0)
                | ui.Slider("limit_min NS ASR (dB)", limit_min=0.0, limit_max=1.0,
                            tooltip="Gain-floor for stationary noise suppression for ASR")
                | RespeakerParam(19, 37, 'float', 1.0, 0.0, 'rw')
        )

        # Gain-floor NN for ASR [-inf..0] dB
        self.limit_min_nn_asr = (
                DataField(0.0)
                | ui.Slider("limit_min NN ASR (dB)", limit_min=0.0, limit_max=1.0,
                            tooltip="Gain-floor for non-stationary noise suppression for ASR")
                | RespeakerParam(19, 38, 'float', 1.0, 0.0, 'rw')
        )

        # Threshold for voice activity detection [-inf..60] dB
        self.gamma_vad_asr = (
                DataField(0.0)
                | ui.Slider("Gamma VAD ASR", limit_min=0.0, limit_max=1000.0,
                            tooltip="Threshold for voice activity detection [-inf..60] dB")
                | RespeakerParam(19, 39, 'float', 1000.0, 0.0, 'rw')
        )

        # Direction-of-arrival angle (read-only)
        self.doa_angle = (
                DataField(0)
                | ui.Number("DOA Angle (°)", readonly=True, tooltip="Current DOA angle (0–359°)")
                | RespeakerParam(21, 0, 'int', 359, 0, 'ro')
        )
