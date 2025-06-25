import duit.ui as ui
from duit.model.DataField import DataField
from duit.ui.ContainerHelper import ContainerHelper

from respeaker2.RespeakerParam import RespeakerParam


class RespeakerConfig:
    def __init__(self):
        container = ContainerHelper(self)

        with container.section("Acoustic Echo Cancellation"):
            self.aec_freeze_on_off = (
                    DataField(0)
                    | ui.Boolean(
                "AEC Freeze Adaptation",
                tooltip="Adaptive Echo Canceler updates inhibit: 0=adaptation enabled, 1=freeze adaptation"
            )
                    | RespeakerParam(18, 7, 'int', 1, 0, 'rw')
            )
            self.aec_norm = (
                    DataField(0.25)
                    | ui.Slider(
                "AEC Norm",
                limit_min=0.25,
                limit_max=16.0,
                tooltip="Limit on norm of AEC filter coefficients"
            )
                    | RespeakerParam(18, 19, 'float', 16.0, 0.25, 'rw')
            )
            self.aec_path_change = (
                    DataField(0)
                    | ui.Boolean(
                "AEC Path Change",
                readonly=True,
                tooltip="AEC Path Change Detection: 0=no change, 1=change detected"
            )
                    | RespeakerParam(18, 25, 'int', 1, 0, 'ro')
            )
            self.rt60 = (
                    DataField(0.25)
                    | ui.Number(
                "RT60 (s)",
                readonly=True,
                tooltip="Current RT60 estimate in seconds"
            )
                    | RespeakerParam(18, 26, 'float', 0.9, 0.25, 'ro')
            )
            self.rt60_on_off = (
                    DataField(0)
                    | ui.Boolean(
                "RT60 Estimation",
                tooltip="RT60 estimation for AES: 0=off, 1=on"
            )
                    | RespeakerParam(18, 28, 'int', 1, 0, 'rw')
            )
            self.aec_silence_level = (
                    DataField(1e-9)
                    | ui.Slider(
                "AEC Silence Level",
                limit_min=1e-9,
                limit_max=1.0,
                tooltip="Threshold for signal detection in AEC [-inf..0] dBov"
            )
                    | RespeakerParam(18, 30, 'float', 1.0, 1e-9, 'rw')
            )
            self.aec_silence_mode = (
                    DataField(0)
                    | ui.Boolean(
                "AEC Far-end Silence",
                readonly=True,
                tooltip="AEC far-end silence detection status: 0=signal, 1=silence"
            )
                    | RespeakerParam(18, 31, 'int', 1, 0, 'ro')
            )

        with container.section("Automatic Gain Control"):
            self.agc_on_off = (
                    DataField(0)
                    | ui.Boolean(
                "AGC On/Off",
                tooltip="Automatic Gain Control: 0=off, 1=on"
            )
                    | RespeakerParam(19, 0, 'int', 1, 0, 'rw')
            )
            self.agc_max_gain = (
                    DataField(1.0)
                    | ui.Slider(
                "AGC Max Gain (dB)",
                limit_min=1.0,
                limit_max=1000.0,
                tooltip="Maximum AGC gain factor [0..60] dB"
            )
                    | RespeakerParam(19, 1, 'float', 1000.0, 1.0, 'rw')
            )
            self.agc_desired_level = (
                    DataField(1e-8)
                    | ui.Slider(
                "AGC Desired Level",
                limit_min=1e-8,
                limit_max=0.99,
                tooltip="Target power level of output signal [-inf..0] dBov"
            )
                    | RespeakerParam(19, 2, 'float', 0.99, 1e-8, 'rw')
            )
            self.agc_gain = (
                    DataField(1.0)
                    | ui.Slider(
                "AGC Gain (dB)",
                limit_min=1.0,
                limit_max=1000.0,
                tooltip="Current AGC gain factor [0..60] dB"
            )
                    | RespeakerParam(19, 3, 'float', 1000.0, 1.0, 'rw')
            )
            self.agc_time_constant = (
                    DataField(0.1)
                    | ui.Slider(
                "AGC Time Constant (s)",
                limit_min=0.1,
                limit_max=1.0,
                tooltip="Ramps up/down time constant in seconds"
            )
                    | RespeakerParam(19, 4, 'float', 1.0, 0.1, 'rw')
            )

        with container.section("Pre-processing"):
            self.hpf_on_off = (
                    DataField(0)
                    | ui.Options(
                "HPF Mode",
                [0, 1, 2, 3],
                tooltip="High-pass filter on mic signals: 0=off,1=70Hz,2=125Hz,3=180Hz"
            )
                    | RespeakerParam(18, 27, 'int', 3, 0, 'rw')
            )

        with container.section("Beamforming"):
            self.beamformer_freeze = (
                    DataField(0)
                    | ui.Boolean(
                "Beamformer Freeze",
                tooltip="Adaptive beamformer updates: 0=enabled,1=freeze"
            )
                    | RespeakerParam(19, 6, 'int', 1, 0, 'rw')
            )

        with container.section("Noise Suppression"):
            self.cni_on_off = (
                    DataField(0)
                    | ui.Boolean(
                "Comfort Noise Insertion",
                tooltip="Comfort noise insertion: 0=off,1=on"
            )
                    | RespeakerParam(19, 5, 'int', 1, 0, 'rw')
            )
            self.stat_noise_suppression = (
                    DataField(0)
                    | ui.Boolean(
                "Stationary Noise Suppression",
                tooltip="Stationary noise suppression: 0=off,1=on"
            )
                    | RespeakerParam(19, 8, 'int', 1, 0, 'rw')
            )
            self.gamma_ns = (
                    DataField(0.0)
                    | ui.Slider(
                "Gamma NS",
                limit_min=0.0,
                limit_max=3.0,
                tooltip="Over-subtraction factor of stationary noise"
            )
                    | RespeakerParam(19, 9, 'float', 3.0, 0.0, 'rw')
            )
            self.min_ns = (
                    DataField(0.0)
                    | ui.Slider(
                "Gain-floor NS (dB)",
                limit_min=0.0,
                limit_max=1.0,
                tooltip="Gain-floor for stationary noise suppression"
            )
                    | RespeakerParam(19, 10, 'float', 1.0, 0.0, 'rw')
            )
            self.nonstat_noise_suppression = (
                    DataField(0)
                    | ui.Boolean(
                "Non-stat. Noise Suppression",
                tooltip="Non-stationary noise suppression: 0=off,1=on"
            )
                    | RespeakerParam(19, 11, 'int', 1, 0, 'rw')
            )
            self.gamma_nn = (
                    DataField(0.0)
                    | ui.Slider(
                "Gamma NN",
                limit_min=0.0,
                limit_max=3.0,
                tooltip="Over-subtraction factor of non-stationary noise"
            )
                    | RespeakerParam(19, 12, 'float', 3.0, 0.0, 'rw')
            )
            self.min_nn = (
                    DataField(0.0)
                    | ui.Slider(
                "Gain-floor NN (dB)",
                limit_min=0.0,
                limit_max=1.0,
                tooltip="Gain-floor for non-stationary noise suppression"
            )
                    | RespeakerParam(19, 13, 'float', 1.0, 0.0, 'rw')
            )

        with container.section("Echo Suppression"):
            self.echo_suppression = (
                    DataField(0)
                    | ui.Boolean(
                "Echo Suppression",
                tooltip="Echo suppression: 0=off,1=on"
            )
                    | RespeakerParam(19, 14, 'int', 1, 0, 'rw')
            )
            self.gamma_e = (
                    DataField(0.0)
                    | ui.Slider(
                "Gamma E",
                limit_min=0.0,
                limit_max=3.0,
                tooltip="Over-subtraction factor of echo (direct & early)"
            )
                    | RespeakerParam(19, 15, 'float', 3.0, 0.0, 'rw')
            )
            self.gamma_e_tail = (
                    DataField(0.0)
                    | ui.Slider(
                "Gamma E Tail",
                limit_min=0.0,
                limit_max=3.0,
                tooltip="Over-subtraction factor of echo tail"
            )
                    | RespeakerParam(19, 16, 'float', 3.0, 0.0, 'rw')
            )
            self.gamma_enl = (
                    DataField(0.0)
                    | ui.Slider(
                "Gamma ENL",
                limit_min=0.0,
                limit_max=5.0,
                tooltip="Over-subtraction factor of non-linear echo"
            )
                    | RespeakerParam(19, 17, 'float', 5.0, 0.0, 'rw')
            )
            self.nlatten_on_off = (
                    DataField(0)
                    | ui.Boolean(
                "Non-linear Echo Attenuation",
                tooltip="Non-linear echo attenuation: 0=off,1=on"
            )
                    | RespeakerParam(19, 18, 'int', 1, 0, 'rw')
            )
            self.nlaec_mode = (
                    DataField(0)
                    | ui.Options(
                "NLAEC Mode",
                [0, 1, 2],
                tooltip="Non-linear AEC training mode: 0=off,1=phase1,2=phase2"
            )
                    | RespeakerParam(19, 20, 'int', 2, 0, 'rw')
            )
            self.transient_echo = (
                    DataField(0)
                    | ui.Boolean(
                "Transient Echo Suppression",
                tooltip="Transient echo suppression: 0=off,1=on"
            )
                    | RespeakerParam(19, 29, 'int', 1, 0, 'rw')
            )

        with container.section("Voice & DOA"):
            self.speech_detected = (
                    DataField(0)
                    | ui.Boolean(
                "Speech Detected",
                readonly=True,
                tooltip="Speech detection status: 0=no speech,1=speech"
            )
                    | RespeakerParam(19, 22, 'int', 1, 0, 'ro')
            )
            self.voice_activity = (
                    DataField(0)
                    | ui.Boolean(
                "Voice Activity",
                readonly=True,
                tooltip="VAD voice activity status: 0=no,1=yes"
            )
                    | RespeakerParam(19, 32, 'int', 1, 0, 'ro')
            )
            self.doa_angle = (
                    DataField(0)
                    | ui.Number(
                "DOA Angle (°)",
                readonly=True,
                tooltip="Current DOA angle (0–359°)"
            )
                    | RespeakerParam(21, 0, 'int', 359, 0, 'ro')
            )

        with container.section("ASR Noise Suppression"):
            self.stat_noise_asr = (
                    DataField(0)
                    | ui.Boolean(
                "Stationary Noise Suppression ASR",
                tooltip="Stationary noise suppression for ASR: 0=off,1=on"
            )
                    | RespeakerParam(19, 33, 'int', 1, 0, 'rw')
            )
            self.nonstat_noise_asr = (
                    DataField(0)
                    | ui.Boolean(
                "Non-stat Noise Suppression ASR",
                tooltip="Non-stationary noise suppression for ASR: 0=off,1=on"
            )
                    | RespeakerParam(19, 34, 'int', 1, 0, 'rw')
            )
            self.gamma_ns_asr = (
                    DataField(0.0)
                    | ui.Slider(
                "Gamma NS ASR",
                limit_min=0.0,
                limit_max=3.0,
                tooltip="Over-subtraction factor of stationary noise for ASR"
            )
                    | RespeakerParam(19, 35, 'float', 3.0, 0.0, 'rw')
            )
            self.gamma_nn_asr = (
                    DataField(0.0)
                    | ui.Slider(
                "Gamma NN ASR",
                limit_min=0.0,
                limit_max=3.0,
                tooltip="Over-subtraction factor of non-stationary noise for ASR"
            )
                    | RespeakerParam(19, 36, 'float', 3.0, 0.0, 'rw')
            )
            self.min_ns_asr = (
                    DataField(0.0)
                    | ui.Slider(
                "Min NS ASR (dB)",
                limit_min=0.0,
                limit_max=1.0,
                tooltip="Gain-floor for stationary noise suppression for ASR"
            )
                    | RespeakerParam(19, 37, 'float', 1.0, 0.0, 'rw')
            )
            self.min_nn_asr = (
                    DataField(0.0)
                    | ui.Slider(
                "Min NN ASR (dB)",
                limit_min=0.0,
                limit_max=1.0,
                tooltip="Gain-floor for non-stationary noise suppression for ASR"
            )
                    | RespeakerParam(19, 38, 'float', 1.0, 0.0, 'rw')
            )
            self.gamma_vad_asr = (
                    DataField(0.0)
                    | ui.Slider(
                "Gamma VAD ASR",
                limit_min=0.0,
                limit_max=1000.0,
                tooltip="Threshold for voice activity detection [-inf..60] dB"
            )
                    | RespeakerParam(19, 39, 'float', 1000.0, 0.0, 'rw')
            )
