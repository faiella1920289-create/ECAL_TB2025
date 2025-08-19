import numpy as np
import eta_phi_ch_map
from scipy import ndimage

def decode_ecal_waves(waves):
    bit13_mask = 1 << 13 #validity bit
    bit12_mask = 1 << 12 #gain bit
    amp_mask   = 0x0FFF #amplitude mask
    is_valid = (waves & bit13_mask) != 0
    gain_is_1 = (waves & bit12_mask) != 0
    amplitudes = waves & amp_mask
    amplitudes[gain_is_1] *= 10
    #amplitudes[~is_valid] = 0
    return amplitudes, is_valid, gain_is_1

def split(waveforms, threshold=20, pre=5, post=10):

    # Assume waveforms is shape (E, C, S)
    E, C, S = waveforms.shape

    # Step 1: Find argmax along sample axis (shape: E x C)
    argmax_idx = np.argmax(waveforms, axis=2)  # shape (E, C)

    # Step 2: Build offsets
    window_offsets = np.arange(-5, 10).reshape(1, 1, -1)         # shape (1,1,15)
    baseline_offsets = np.arange(-15, -5).reshape(1, 1, -1)      # shape (1,1,10)

    # Expand argmax index for broadcasting
    argmax_exp = argmax_idx[:, :, np.newaxis]  # shape (E, C, 1)

    # Add offsets and wrap with modulo S to stay in bounds
    window_indices   = (argmax_exp + window_offsets) % S        # shape (E, C, 15)
    baseline_indices = (argmax_exp + baseline_offsets) % S      # shape (E, C, 10)

    # Build broadcasted event/channel indices
    event_idx = np.arange(E)[:, None, None]
    chan_idx  = np.arange(C)[None, :, None]

    # Extract waveform windows and baseline windows
    window_waveforms   = waveforms[event_idx, chan_idx, window_indices]      # (E, C, 15)
    baseline_waveforms = waveforms[event_idx, chan_idx, baseline_indices]    # (E, C, 10)

    # Step 3: Compute baseline mean
    baseline = np.mean(baseline_waveforms, axis=2)  # shape (E, C)

    return argmax_idx, baseline, window_waveforms


def find_5x5(charge_mean, ieta, iphi):
    fake_mask = np.full(ieta.shape, True)
    mask_5x5 = np.full(ieta.shape, True)

    while True:
      charge_mean[~fake_mask] = 0
      seed_ch = np.argmax(charge_mean)
      ieta_seed, iphi_seed = ieta[seed_ch], iphi[seed_ch]
      mask_5x5 = np.logical_and(np.abs(ieta - ieta_seed) < 3, np.abs(iphi - iphi_seed) < 3)
      mask_5x5[seed_ch] = False
      seed_5x5_ratio = np.sum(charge_mean[mask_5x5]) * 24/np.sum(mask_5x5) / charge_mean[seed_ch]
      if seed_5x5_ratio < 0.2:
        fake_mask[seed_ch] = False
        continue
      else:
        mask_5x5[seed_ch] = True
        break
    return mask_5x5, seed_ch



def generic_reco(
  waves, detector_name,
  signal_samples_pre_peak=5, signal_samples_post_peak=10,
  charge_zerosup_peak_threshold=10, seed_charge_threshold=50,
  do_5x5=True,
  do_timing=False, rise_samples_pre_peak=5, rise_samples_post_peak=2, sampling_rate=5, cf=0.12, interpolation_factor=20
):

  max_idx, baselines, signal_window = split(waves, pre=signal_samples_pre_peak, post=signal_samples_post_peak)

  # mean of all values
  values_mean = np.mean(waves, axis=2)

  waves = waves - np.repeat(baselines[:, :, np.newaxis], waves.shape[2], axis=2)  # baseline subtraction

  signal_window = signal_window - np.repeat(baselines[:, :, np.newaxis], signal_window.shape[2], axis=2)

  # Build event and channel indices
  event_idx = np.arange(waves.shape[0])[:, None]        # shape (E, 1)
  chan_idx  = np.arange(waves.shape[1])[None, :]        # shape (1, C)
  values_max = waves[event_idx, chan_idx, max_idx]  # shape (E, C)

  mask_under_thr = values_max < charge_zerosup_peak_threshold

  charge = np.sum(signal_window, axis=2)
  charge[mask_under_thr] = 0

  tWave = np.repeat(np.arange(0, waves.shape[2])[np.newaxis, :], charge.shape[1], axis=0)
  tWave = np.repeat(tWave[np.newaxis, :], charge.shape[0], axis=0)
  ich = np.repeat(np.arange(0, waves.shape[1])[np.newaxis, :], charge.shape[0], axis=0)


  return_dict = {}
  mask_selected_events = np.ones((charge.shape[0],), dtype=bool)
  det = detector_name


  if do_5x5:
    charge_mean = np.mean(charge, axis=0)
    seed_ch = -999
    ieta, iphi = eta_phi_ch_map.eta_phi_ch_map()

    mask_5x5, seed_ch = find_5x5(charge_mean, ieta, iphi)

    charge_seed = charge[:, seed_ch]
    mask_low_charge_seed = charge_seed > seed_charge_threshold

    # amplitude_map of the 5x5 matrix
    charge_sum_5x5 = np.sum(charge[:, mask_5x5], axis=1)
    charge_fraction_5x5 = charge / charge_sum_5x5[:, np.newaxis]

    ieta_centroid = charge_fraction_5x5[:, mask_5x5] @ ieta[mask_5x5]
    iphi_centroid = charge_fraction_5x5[:, mask_5x5] @ iphi[mask_5x5]

    ieta = np.repeat(ieta[np.newaxis, :], charge.shape[0], axis=0)
    iphi = np.repeat(iphi[np.newaxis, :], charge.shape[0], axis=0)

    iphi_within_5x5 = iphi - iphi[0, seed_ch]
    ieta_within_5x5 = ieta - ieta[0, seed_ch]

    seed_ch = np.repeat(np.ones(1,)*seed_ch, charge_sum_5x5.shape[0], axis=0)

    return_dict.update({
      f"{det}_charge_sum_5x5": charge_sum_5x5, f"{det}_charge_seed": charge_seed,
      f"{det}_iphi_within_5x5": iphi_within_5x5, f"{det}_ieta_within_5x5": ieta_within_5x5,
      f"{det}_ieta": ieta, f"{det}_iphi": iphi,
      f"{det}_charge_divided_5x5": charge_fraction_5x5, f"{det}_seed_ch": seed_ch,
      f"{det}_ieta_centroid": ieta_centroid, f"{det}_iphi_centroid": iphi_centroid
    })

    mask_selected_events = mask_low_charge_seed

  if do_timing:
    rise = signal_window[:, :, (signal_samples_pre_peak - rise_samples_pre_peak):(signal_samples_pre_peak + rise_samples_post_peak)]
    rise_interp = ndimage.zoom(rise, [1, 1, interpolation_factor])

    peak_interp = rise_interp.max(axis=2)

    pseudo_t = np.argmax(rise_interp > np.repeat((peak_interp*cf)[:, :, np.newaxis], rise_interp.shape[2], axis=2), axis=2).astype(float)
    pseudo_t /= float(sampling_rate*interpolation_factor)
    pseudo_t += (max_idx / sampling_rate)
    return_dict.update({f"{det}_cf_time": pseudo_t, f"{det}_peak_interp": peak_interp})

  return_dict.update({
    f"{det}_peak_pos": max_idx, f"{det}_ich": ich,
    f"{det}_samples_mean": values_mean, f"{det}_peak": values_max, f"{det}_charge": charge,
    f"{det}_wave": waves, f"{det}_t_wave": tWave
  })


  return mask_selected_events, return_dict
