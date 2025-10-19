import numpy as np
import awkward as ak
from scipy import ndimage
import multiprocessing as mp

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


def split(waveforms, threshold=20, pre=5, post=10, baseline_samples=10):

    # Assume waveforms is shape (E, C, S)
    E, C, S = waveforms.shape

    # Step 1: Find argmax along sample axis (shape: E x C)
    argmax_idx = np.argmax(waveforms, axis=2)  # shape (E, C)

    # Step 2: Build offsets
    window_offsets = np.arange(-int(pre), int(post)).reshape(1, 1, -1)         # shape (1,1,15)
    baseline_offsets = np.arange(-int(pre)-int(baseline_samples), -int(pre)).reshape(1, 1, -1)      # shape (1,1,10)

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
    baseline = np.mean(baseline_waveforms, axis=2)       # shape (E, C)
    baseline_std = np.std(baseline_waveforms, axis=2)    # shape (E, C)
    baseline_integral = np.sum(baseline_waveforms, axis=2)  # shape (E, C)

    return argmax_idx, baseline, baseline_std, baseline_integral, window_waveforms


def find_5x5(charge_mean, ieta, iphi):
    fake_mask = np.full(ieta.shape, True)
    mask_5x5 = np.full(ieta.shape, True)

    while True:
      charge_mean[~fake_mask] = 0
      seed_ch = np.argmax(charge_mean)
      ieta_seed, iphi_seed = ieta[seed_ch], iphi[seed_ch]
      mask_5x5 = np.logical_and(np.abs(ieta - ieta_seed) < 3, np.abs(iphi - iphi_seed) < 3)
      mask_5x5[seed_ch] = False
      seed_5x5_ratio = np.sum(charge_mean[mask_5x5]) * 24 / np.sum(mask_5x5) / charge_mean[seed_ch]
      if seed_5x5_ratio < 0.2:
        fake_mask[seed_ch] = False
        continue
      else:
        mask_5x5[seed_ch] = True
        break
    return mask_5x5, seed_ch


def generic_reco(
  waves, detector_name, opt, id=None, geo_dict=None,
  signal_samples_pre_peak: int=5, signal_samples_post_peak: int=10,
  charge_zerosup_peak_threshold=10, seed_charge_threshold=50,
  do_5x5=True, timing_method="cf", timing_thr=None, baseline_subtract=True,
  do_timing=False, save_some_waves=True, rise_samples_pre_peak: int=5, rise_samples_post_peak: int=2, sampling_rate=5, cf=0.12, interpolation_factor=20, baseline_samples=10
):

  max_idx, baselines, baselines_std, baseline_integral, signal_window = split(waves, pre=signal_samples_pre_peak, post=signal_samples_post_peak)
  # print(baseline_integral.shape)

  values_mean = np.mean(waves, axis=2) # mean of all values
  values_std = np.std(waves, axis=2)   # std of all values
  if baseline_subtract:
    waves = waves - np.repeat(baselines[:, :, np.newaxis], waves.shape[2], axis=2)  # baseline subtraction
    signal_window = signal_window - np.repeat(baselines[:, :, np.newaxis], signal_window.shape[2], axis=2) # baseline subtraction in the signal window

  # Build event and channel indices
  event_idx = np.arange(waves.shape[0])[:, None]        # shape (E, 1)
  chan_idx  = np.arange(waves.shape[1])[None, :]        # shape (1, C)
  values_max = waves[event_idx, chan_idx, max_idx]      # shape (E, C)

  # zero suppression threshold mask
  mask_under_thr = values_max < charge_zerosup_peak_threshold

  charge = np.sum(signal_window, axis=2)
  charge[mask_under_thr] = 0

  tWave = np.repeat(np.arange(0, waves.shape[2])[np.newaxis, :], charge.shape[1], axis=0)/sampling_rate
  tWave = np.repeat(tWave[np.newaxis, :], charge.shape[0], axis=0)
  ich = np.repeat(np.arange(0, waves.shape[1])[np.newaxis, :], charge.shape[0], axis=0)

  return_dict = {}
  mask_selected_events = np.ones((charge.shape[0],), dtype=bool)
  det = detector_name


  if id is not None:
    for var in id:
      return_dict.update({f"{det}_{var}": np.repeat(id[var][np.newaxis, :], waves.shape[0], axis=0)})


  if geo_dict is not None:
    ieta, iphi = geo_dict["ieta"], geo_dict["iphi"]

    if do_5x5:
      charge_mean = np.mean(charge, axis=0)
      seed_ch = -999

      mask_5x5, seed_ch = find_5x5(charge_mean, ieta, iphi)

      charge_seed = charge[:, seed_ch]
      mask_low_charge_seed = charge_seed > seed_charge_threshold

    # amplitude_map of the 5x5 matrix
      charge_sum_5x5 = np.sum(charge[:, mask_5x5], axis=1)
      charge_fraction_5x5 = charge / charge_sum_5x5[:, np.newaxis]

      ieta_centroid = charge_fraction_5x5[:, mask_5x5] @ ieta[mask_5x5]
      iphi_centroid = charge_fraction_5x5[:, mask_5x5] @ iphi[mask_5x5]

      iphi_within_5x5 = iphi - iphi[seed_ch]
      ieta_within_5x5 = ieta - ieta[seed_ch]

      ieta_within_5x5 = np.repeat(ieta_within_5x5[np.newaxis, :], charge.shape[0], axis=0)
      iphi_within_5x5 = np.repeat(iphi_within_5x5[np.newaxis, :], charge.shape[0], axis=0)

      seed_ch = np.repeat(np.ones(1,)*seed_ch, charge_sum_5x5.shape[0], axis=0)

      return_dict.update({
        f"{det}_charge_sum_5x5": charge_sum_5x5, f"{det}_charge_seed": charge_seed,
        f"{det}_iphi_within_5x5": iphi_within_5x5, f"{det}_ieta_within_5x5": ieta_within_5x5,
        f"{det}_charge_divided_5x5": charge_fraction_5x5, f"{det}_seed_ch": seed_ch,
        f"{det}_ieta_centroid": ieta_centroid, f"{det}_iphi_centroid": iphi_centroid
      })

      #mask_selected_events = mask_low_charge_seed

    ieta = np.repeat(ieta[np.newaxis, :], charge.shape[0], axis=0)
    iphi = np.repeat(iphi[np.newaxis, :], charge.shape[0], axis=0)
    return_dict.update({
      f"{det}_ieta": ieta, f"{det}_iphi": iphi
    })

  if do_timing:
    if do_5x5: timing_mask = mask_5x5
    else: timing_mask = np.full((signal_window.shape[1],), True)

    timing_nch = int(np.sum(timing_mask))
    print(f"timing nch: {timing_nch}")
    rise = np.zeros((signal_window.shape[0], timing_nch, rise_samples_pre_peak+rise_samples_post_peak))
    rise = signal_window[:, timing_mask, signal_samples_pre_peak - rise_samples_pre_peak:signal_samples_pre_peak + rise_samples_post_peak]
    rise_interp = ndimage.zoom(rise, [1, 1, interpolation_factor])

    if timing_method == "cf":
      peak_interp = rise_interp.max(axis=2) #shape: (Events, Channel) - on y axis
      thresholds = peak_interp*cf #values_max*cf
      #return_dict.update({f"{det}_interp": interp})

    elif timing_method == "fixed_thr":
      print(rise)
      thresholds = np.ones((rise.shape[0], rise.shape[1]))*timing_thr

    else:
      raise NotImplemented(f"method: {timing_method} not implemented")

    pseudo_t = np.zeros((signal_window.shape[0], signal_window.shape[1]))
    print(f"thresholds, rise_interp shapes: {thresholds.shape}, {rise_interp.shape}")
    pseudo_t[:, timing_mask] = np.argmax(rise_interp > np.repeat((thresholds)[:, :, np.newaxis], rise_interp.shape[2], axis=2), axis=2).astype(float)
    pseudo_t[:, timing_mask] += np.random.uniform(low=-0.5, high=0.5, size=(pseudo_t.shape[0], timing_nch))
    pseudo_t[:, timing_mask] /= float(sampling_rate*interpolation_factor)
    pseudo_t[:, timing_mask] += ((max_idx[:, timing_mask] - rise_samples_pre_peak) / sampling_rate)
    return_dict.update({f"{det}_{timing_method}_time": pseudo_t})

  return_dict.update({
    f"{det}_peak_pos": max_idx, f"{det}_ich": ich,
    f"{det}_samples_mean": values_mean, f"{det}_peak": values_max, f"{det}_samples_std": values_std,
    f"{det}_baseline_mean": baselines, f"{det}_baseline_std": baselines_std, f"{det}_baseline_integral": baseline_integral/baseline_samples*signal_window.shape[2],
    f"{det}_charge": charge
  })

  if save_some_waves:
    drop_waves_mask = np.random.uniform(size=(waves.shape[0],)) > 3/max(50, waves.shape[0])
    waves[drop_waves_mask, ...] = 0
    tWave[drop_waves_mask, ...] = 0
    return_dict.update({f"{det}_waves": waves, f"{det}_tWave": tWave, f"{det}_wave_dropped": drop_waves_mask})

  return mask_selected_events, return_dict


def hodo_reco(tree, detector_name):
  det = detector_name
  reco_dict = {}
  coords_list = ["x1", "x2", "y1", "y2"]
  branches = tree.arrays(
    [f"{det}_{coord}_nclusters" for coord in coords_list] +
    [f"{det}_{coord}_pos" for coord in coords_list],
    library="ak"
  )
  mask_dict = np.ones(len(branches[f"{det}_{coords_list[0]}_nclusters"]), dtype=bool)
  for coord in coords_list:
    clus = branches[f"{det}_{coord}_nclusters"]
    pos = branches[f"{det}_{coord}_pos"]
    mask = (clus > 0)
    pos_first_cluster = ak.to_numpy(ak.where(mask, ak.firsts(pos), -999))
    mask_single_cluster = ak.to_numpy(clus == 1)
    average_all_clusters = ak.to_numpy(ak.where(mask, ak.sum(pos, axis=1) / clus, -999.0 ))
    reco_dict.update({
      f"{det}_{coord}_cl0_pos": pos_first_cluster,
      f"{det}_{coord}_single_cl_flag": mask_single_cluster,
      f"{det}_{coord}_avg_pos": average_all_clusters,
    })

  return mask_dict, reco_dict


def bcp_reco(bcp_clk, detector_name):
  det = detector_name
  reco_dict = {}
  mask = np.ones((bcp_clk.shape[0],), dtype=bool)
  bcp_clk = bcp_clk.astype(np.int64)
  bcp1_clk = bcp_clk[:, 0, :]
  bcp2_clk = bcp_clk[:, 1, :]
  bcp1_clk_mean = np.tile(np.mean(bcp1_clk, axis=0), (bcp1_clk.shape[0], 1))
  bcp2_clk_mean = np.tile(np.mean(bcp2_clk, axis=0), (bcp2_clk.shape[0], 1))
  reco_dict.update({f"{det}1_clk": bcp1_clk, f"{det}2_clk": bcp2_clk,
    f"{det}1_clk_mean": bcp1_clk_mean.astype(int), f"{det}2_clk_mean": bcp2_clk_mean.astype(int)
  })

  return mask, reco_dict


def generic_reco_chunk(args):
    """
    Wrapper to handle chunking for multiprocessing.
    """
    print("started chunk")
    try:
        waves, det, opt, kwargs = args
        return generic_reco(waves, det, opt, **kwargs)
    except Exception:
        print(traceback.format_exc(), file=sys.stderr, flush=True)


def generic_reco_parallel(waves, detector_name, opt, n_cpus=2, **kwargs):
    E = waves.shape[0]
    chunk_size = (E + n_cpus - 1) // n_cpus  # ceil division
    chunks = [(waves[i*chunk_size:(i+1)*chunk_size], detector_name, opt, kwargs)
              for i in range(n_cpus)]

    print("opening pool")
    results = [generic_reco_chunk(chunk) for chunk in chunks]

#    try:
#        ctx = mp.get_context("spawn")
#        with ctx.Pool(n_cpus) as pool:
#            results = pool.imap_unordered(generic_reco_chunk, chunks)
#    except BrokenPipeError:
#        print("\n\n\nRECO_PARALLEL in broken pipe: FALLING BACK TO SERIAL\n\n")
#        for chunk in chunks: generic_reco_chunk(chunk)
#    except Exception:
#        print("\n\n\nRECO_PARALLEL in broken pipe: FALLING BACK TO SERIAL\n\n")
#        for chunk in chunks: generic_reco_chunk(chunk)

    # Combine results
    masks_list, dicts_list = zip(*results)
    combined_mask = np.concatenate(masks_list, axis=0)

    combined_dict = {}
    for key in dicts_list[0].keys():
        combined_dict[key] = np.concatenate([d[key] for d in dicts_list], axis=0)

    return combined_mask, combined_dict
