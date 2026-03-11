import time
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


def split(waveforms, threshold=None, pre=5, post=10, baseline_samples=10):

    # Assume waveforms is shape (E, C, S)
    E, C, S = waveforms.shape

    if threshold is not None:
      argmax_idx = np.argmax(waveforms > threshold, axis=2)  # shape (E, C)
    else:
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


def find_5x5(charge_mean, ieta, iphi, fixed_5x5=None):
    fake_mask = np.full(ieta.shape, True)
    mask_5x5 = np.full(ieta.shape, True)


    while True:
      if fixed_5x5:
          seed_ch = np.argmax(np.logical_and(ieta==fixed_5x5[0],iphi==fixed_5x5[1]))
          print(f"Seed channel: {seed_ch}", flush=True)
      else:
        charge_mean[~fake_mask] = 0
        seed_ch = np.argmax(charge_mean)
      ieta_seed, iphi_seed = ieta[seed_ch], iphi[seed_ch]
      mask_5x5 = np.logical_and(np.abs(ieta - ieta_seed) < 3, np.abs(iphi - iphi_seed) < 3)
      mask_5x5[seed_ch] = False
      seed_5x5_ratio = np.sum(charge_mean[mask_5x5]) * 24 / np.sum(mask_5x5) / charge_mean[seed_ch]
      mask_5x5[seed_ch] = True
      if fixed_5x5: return mask_5x5, seed_ch
      if seed_5x5_ratio < 0.2:
        fake_mask[seed_ch] = False
        continue
      else:
        break
    print(f"Seed channel: {seed_ch}", flush=True)
    return mask_5x5, seed_ch


def generic_reco(waves, detector_name, **kwargs):

  globals().update(kwargs)

  t0 = time.time()

  max_idx, baselines, baselines_std, baseline_integral, signal_window = split(waves, pre=signal_samples_pre_peak, post=signal_samples_post_peak, threshold=threshold_not_using_peak)
  # print(baseline_integral.shape)

  print(f"baselines took: {time.time() - t0}")
  t0 = time.time()

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

  print(f"all chs things took: {time.time() - t0}")
  t0 = time.time()


  if geo_dict is not None:
    ieta, iphi = geo_dict["ieta"], geo_dict["iphi"]

    if do_5x5:
      charge_mean = np.mean(charge, axis=0)
      seed_ch = -999

      mask_5x5, seed_ch = find_5x5(charge_mean, ieta, iphi, fixed_5x5=fixed_5x5)
      print(f"find 5x5 took: {time.time() - t0}")
      t0 = time.time()


      charge_seed = charge[:, seed_ch]
      charge_sum_5x5 = np.sum(charge[:, mask_5x5], axis=1)
      charge_sum_5x5 = np.clip(charge_sum_5x5, seed_charge_threshold, None)

      mask_low_charge_seed = charge_seed > seed_charge_threshold

    # amplitude_map of the 5x5 matrix
      w0=3.8
      charge_fraction_5x5 = np.zeros(charge.shape)
      charge_fraction_5x5[:, mask_5x5] = charge[:, mask_5x5] / charge_sum_5x5[:, np.newaxis]

      print(f"seed/5x5/fractions took: {time.time() - t0}")
      t0 = time.time()


      w_log = np.maximum(0.0,w0+np.log(np.clip(charge / charge_sum_5x5[:, np.newaxis], 1e-8, None)))
      w_log /= (np.sum(w_log, axis=1, keepdims=True))

      ieta_centroid = w_log[:, mask_5x5] @ ieta[mask_5x5]
      iphi_centroid = w_log[:, mask_5x5] @ iphi[mask_5x5]

      print(f"centrois took: {time.time() - t0}")
      t0 = time.time()


      iphi_within_5x5 = np.zeros(iphi.shape)
      ieta_within_5x5 = np.zeros(ieta.shape)

      iphi_within_5x5[mask_5x5] = iphi[mask_5x5] - iphi[seed_ch]
      ieta_within_5x5[mask_5x5] = ieta[mask_5x5] - ieta[seed_ch]

      ieta_within_5x5 = np.repeat(ieta_within_5x5[np.newaxis, :], charge.shape[0], axis=0)
      iphi_within_5x5 = np.repeat(iphi_within_5x5[np.newaxis, :], charge.shape[0], axis=0)

      print(f"ieta within 5x5 (+iphi) took: {time.time() - t0}")
      t0 = time.time()


      seed_ch_app = seed_ch
      seed_ch = np.repeat(np.ones(1,)*seed_ch, charge_sum_5x5.shape[0], axis=0)

      highest_ch = np.argmax(charge * mask_5x5, axis=1)
      highest_charge = np.take_along_axis(charge, highest_ch[:, None], axis=1).squeeze()
      highest_peak = np.take_along_axis(values_max, highest_ch[:, None], axis=1).squeeze()

      print(f"highest ch took: {time.time() - t0}")
      t0 = time.time()

      print(f"tau took: {time.time() - t0}")
      t0 = time.time()

      return_dict.update({
        f"{det}_charge_sum_5x5": charge_sum_5x5, f"{det}_charge_seed": charge_seed, f"{det}_seed_over_5x5": charge_fraction_5x5[:, seed_ch_app],
        f"{det}_highest_charge_over_5x5": highest_charge/charge_sum_5x5,
        f"{det}_iphi_within_5x5": iphi_within_5x5, f"{det}_ieta_within_5x5": ieta_within_5x5,
        f"{det}_charge_divided_5x5": charge_fraction_5x5, f"{det}_seed_ch": seed_ch,
        f"{det}_ieta_centroid": ieta_centroid, f"{det}_iphi_centroid": iphi_centroid,
        f"{det}_highest_ch": highest_ch, f"{det}_highest_charge": highest_charge, f"{det}_highest_peak": highest_peak,
      })

      #mask_selected_events = mask_low_charge_seed

    ieta = np.repeat(ieta[np.newaxis, :], charge.shape[0], axis=0)
    iphi = np.repeat(iphi[np.newaxis, :], charge.shape[0], axis=0)

  if do_tau:
      if do_5x5: tau_mask = mask_5x5
      else: tau_mask = np.full((signal_window.shape[1],), True)

      descent = signal_window[:, tau_mask, signal_samples_pre_peak+1:signal_samples_pre_peak+tau_descent_samples+1]
      log_w = np.log(np.clip(descent, 1, None))
      log_slopes = np.diff(log_w, axis=2) / descent.shape[2]
      tau = np.zeros(charge.shape)
      tau[:, tau_mask] = -1.0 / (np.median(log_slopes, axis=2) * sampling_rate)
      return_dict.update({f"{det}_tau": tau})

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

  per_ch_info = {
    f"{det}_peak_pos": max_idx, f"{det}_peak_time": max_idx/sampling_rate,
    f"{det}_charge": charge, f"{det}_peak": values_max, f"{det}_baseline_mean": baselines,
    f"{det}_baseline_std": baselines_std, f"{det}_baseline_integral": baseline_integral/baseline_samples*signal_window.shape[2],
  }
  if save_mean_rms_all_samples:
    per_ch_info.update({f"{det}_samples_mean": values_mean, f"{det}_samples_std": values_std})
  if geo_dict is not None:
    per_ch_info.update({f"{det}_ieta": ieta, f"{det}_iphi": iphi})
  if id is not None:
    for var in id:
      per_ch_info.update({f"{det}_{var}": np.repeat(id[var][np.newaxis, :], waves.shape[0], axis=0)})

  if do_5x5 and save_only_5x5_info:
    for key in per_ch_info:
      return_dict[key] = np.zeros(per_ch_info[key].shape)
      return_dict[key][:, mask_5x5] = per_ch_info[key][:, mask_5x5]
  else:
    return_dict.update(per_ch_info)

  if save_some_waves:
    drop_waves_mask = np.ones(waves.shape[0], dtype=bool)
    zero_indices = np.random.choice(waves.shape[0], size=min(10, waves.shape[0]), replace=False)
    drop_waves_mask[zero_indices] = False
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
        waves, det, kwargs = args
        return generic_reco(waves, det, **kwargs)
    except Exception:
        print(traceback.format_exc(), file=sys.stderr, flush=True)


def generic_reco_parallel(waves, detector_name, n_cpus=2, **kwargs):
    E = waves.shape[0]
    chunk_size = (E + n_cpus - 1) // n_cpus  # ceil division
    chunks = [(waves[i*chunk_size:(i+1)*chunk_size], detector_name, kwargs)
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
