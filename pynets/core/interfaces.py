#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 10 15:44:46 2017
Copyright (C) 2017
@author: Derek Pisner (dPys)
"""
from nipype.interfaces.base import (BaseInterface, BaseInterfaceInputSpec, TraitedSpec, File, traits, SimpleInterface,
                                    Directory)


class NetworkAnalysisInputSpec(BaseInterfaceInputSpec):
    """Input interface wrapper for NetworkAnalysis"""
    ID = traits.Any(mandatory=True)
    network = traits.Any(mandatory=False)
    thr = traits.Any(mandatory=True)
    conn_model = traits.Str(mandatory=True)
    est_path = File(exists=True, mandatory=True)
    roi = traits.Any(mandatory=False)
    prune = traits.Any(mandatory=False)
    norm = traits.Any(mandatory=False)
    binary = traits.Bool(False, usedefault=True)


class NetworkAnalysisOutputSpec(TraitedSpec):
    """Output interface wrapper for NetworkAnalysis"""
    out_path_neat = File(exists=True, mandatory=True)


class NetworkAnalysis(BaseInterface):
    """Interface wrapper for NetworkAnalysis"""
    input_spec = NetworkAnalysisInputSpec
    output_spec = NetworkAnalysisOutputSpec

    def _run_interface(self, runtime):
        from pynets.stats.netstats import extractnetstats
        out = extractnetstats(
            self.inputs.ID,
            self.inputs.network,
            self.inputs.thr,
            self.inputs.conn_model,
            self.inputs.est_path,
            self.inputs.roi,
            self.inputs.prune,
            self.inputs.norm,
            self.inputs.binary)
        setattr(self, '_outpath', out)
        return runtime

    def _list_outputs(self):
        import os.path as op
        return {'out_path_neat': op.abspath(getattr(self, '_outpath'))}


class CombineOutputsInputSpec(BaseInterfaceInputSpec):
    """Input interface wrapper for CombineOutputs"""
    ID = traits.Any(mandatory=True)
    network = traits.Any(mandatory=False)
    net_mets_csv_list = traits.List(mandatory=True)
    plot_switch = traits.Bool(False, usedefault=True)
    multi_nets = traits.Any(mandatory=False)
    multimodal = traits.Bool(False, usedefault=True)


class CombineOutputsOutputSpec(TraitedSpec):
    """Output interface wrapper for CombineOutputs"""
    combination_complete = traits.Bool()


class CombineOutputs(SimpleInterface):
    """Interface wrapper for CombineOutputs"""
    input_spec = CombineOutputsInputSpec
    output_spec = CombineOutputsOutputSpec

    def _run_interface(self, runtime):
        from pynets.core.utils import collect_pandas_df
        combination_complete = collect_pandas_df(
            self.inputs.network,
            self.inputs.ID,
            self.inputs.net_mets_csv_list,
            self.inputs.plot_switch,
            self.inputs.multi_nets,
            self.inputs.multimodal)
        setattr(self, '_combination_complete', combination_complete)
        return runtime

    def _list_outputs(self):
        return {'combination_complete': getattr(self, '_combination_complete')}


class _IndividualClusteringInputSpec(BaseInterfaceInputSpec):
    """Input interface wrapper for IndividualClustering"""
    func_file = File(exists=True, mandatory=True)
    conf = traits.Any(mandatory=False)
    clust_mask = File(exists=True, mandatory=True)
    ID = traits.Any(mandatory=True)
    k = traits.Any(mandatory=True)
    clust_type = traits.Str(mandatory=True)
    vox_size = traits.Str('2mm', mandatory=True, usedefault=True)
    local_corr = traits.Str('allcorr', mandatory=True, usedefault=True)
    mask = traits.Any(mandatory=False)


class _IndividualClusteringOutputSpec(TraitedSpec):
    """Output interface wrapper for IndividualClustering"""
    uatlas = File(exists=True)
    atlas = traits.Str(mandatory=True)
    clustering = traits.Bool(True, usedefault=True)
    clust_mask = File(exists=True, mandatory=True)
    k = traits.Any(mandatory=True)
    clust_type = traits.Str(mandatory=True)


class IndividualClustering(SimpleInterface):
    """Interface wrapper for IndividualClustering"""
    input_spec = _IndividualClusteringInputSpec
    output_spec = _IndividualClusteringOutputSpec

    def _run_interface(self, runtime):
        import gc
        from nipype.utils.filemanip import fname_presuffix, copyfile
        from pynets.fmri import clustools
        from pynets.registration.reg_utils import check_orient_and_dims

        clust_list = ['kmeans', 'ward', 'complete', 'average', 'ncut', 'rena']

        clust_mask_temp_path = check_orient_and_dims(self.inputs.clust_mask, self.inputs.vox_size,
                                                     outdir=runtime.cwd)

        if self.inputs.mask:
            out_name_mask = fname_presuffix(self.inputs.mask, suffix='_tmp', newpath=runtime.cwd)
            copyfile(self.inputs.mask, out_name_mask, copy=True, use_hardlink=False)
        else:
            out_name_mask = None

        out_name_func_file = fname_presuffix(self.inputs.func_file, suffix='_tmp', newpath=runtime.cwd)
        copyfile(self.inputs.func_file, out_name_func_file, copy=True, use_hardlink=False)

        if self.inputs.conf:
            out_name_conf = fname_presuffix(self.inputs.conf, suffix='_tmp', newpath=runtime.cwd)
            copyfile(self.inputs.conf, out_name_conf, copy=True, use_hardlink=False)
        else:
            out_name_conf = None

        nip = clustools.NiParcellate(func_file=out_name_func_file,
                                     clust_mask=clust_mask_temp_path,
                                     k=self.inputs.k,
                                     clust_type=self.inputs.clust_type,
                                     local_corr=self.inputs.local_corr,
                                     conf=out_name_conf,
                                     mask=out_name_mask)

        atlas = nip.create_clean_mask()
        nip.create_local_clustering(overwrite=True, r_thresh=0.4)

        if self.inputs.clust_type in clust_list:
            uatlas = nip.parcellate()
        else:
            raise ValueError('Clustering method not recognized. '
                             'See: https://nilearn.github.io/modules/generated/nilearn.regions.Parcellations.'
                             'html#nilearn.regions.Parcellations')
        del nip
        gc.collect()

        self._results['atlas'] = atlas
        self._results['uatlas'] = uatlas
        self._results['clust_mask'] = self.inputs.clust_mask
        self._results['k'] = self.inputs.k
        self._results['clust_type'] = self.inputs.clust_type
        self._results['clustering'] = True
        return runtime


class _ExtractTimeseriesInputSpec(BaseInterfaceInputSpec):
    """Input interface wrapper for ExtractTimeseries"""
    conf = traits.Any(mandatory=False)
    func_file = File(exists=True, mandatory=True)
    coords = traits.Any(mandatory=True)
    roi = traits.Any(mandatory=False)
    dir_path = traits.Str(mandatory=True)
    ID = traits.Any(mandatory=True)
    network = traits.Any(mandatory=False)
    smooth = traits.Any(mandatory=True)
    atlas = traits.Any(mandatory=True)
    uatlas = traits.Any(mandatory=False)
    labels = traits.Any(mandatory=True)
    c_boot = traits.Any(mandatory=False)
    block_size = traits.Any(mandatory=False)
    hpass = traits.Any(mandatory=True)
    mask = traits.Any(mandatory=False)
    parc = traits.Bool()
    node_size = traits.Any(mandatory=False)
    net_parcels_nii_path = traits.Any(mandatory=False)


class _ExtractTimeseriesOutputSpec(TraitedSpec):
    """Output interface wrapper for ExtractTimeseries"""
    ts_within_nodes = traits.Any(mandatory=True)
    node_size = traits.Any(mandatory=True)
    smooth = traits.Any(mandatory=True)
    dir_path = traits.Str(mandatory=True)
    atlas = traits.Any(mandatory=True)
    uatlas = traits.Any(mandatory=True)
    labels = traits.Any(mandatory=True)
    coords = traits.Any(mandatory=True)
    c_boot = traits.Any(mandatory=True)
    hpass = traits.Any(mandatory=True)
    roi = traits.Any(mandatory=True)


class ExtractTimeseries(SimpleInterface):
    """Interface wrapper for ExtractTimeseries"""
    input_spec = _ExtractTimeseriesInputSpec
    output_spec = _ExtractTimeseriesOutputSpec

    def _run_interface(self, runtime):
        import gc
        from nipype.utils.filemanip import fname_presuffix, copyfile
        from pynets.fmri import estimation

        if self.inputs.net_parcels_nii_path:
            out_name_net_parcels_nii_path = fname_presuffix(self.inputs.net_parcels_nii_path, suffix='_tmp',
                                                            newpath=runtime.cwd)
            copyfile(self.inputs.net_parcels_nii_path, out_name_net_parcels_nii_path, copy=True, use_hardlink=False)
        else:
            out_name_net_parcels_nii_path = None
        if self.inputs.mask:
            out_name_mask = fname_presuffix(self.inputs.mask, suffix='_tmp', newpath=runtime.cwd)
            copyfile(self.inputs.mask, out_name_mask, copy=True, use_hardlink=False)
        else:
            out_name_mask = None
        out_name_func_file = fname_presuffix(self.inputs.func_file, suffix='_tmp', newpath=runtime.cwd)
        copyfile(self.inputs.func_file, out_name_func_file, copy=True, use_hardlink=False)

        if self.inputs.conf:
            out_name_conf = fname_presuffix(self.inputs.conf, suffix='_tmp', newpath=runtime.cwd)
            copyfile(self.inputs.conf, out_name_conf, copy=True, use_hardlink=False)
        else:
            out_name_conf = None

        te = estimation.TimeseriesExtraction(net_parcels_nii_path=out_name_net_parcels_nii_path,
                                             node_size=self.inputs.node_size,
                                             conf=out_name_conf,
                                             func_file=out_name_func_file,
                                             coords=self.inputs.coords,
                                             roi=self.inputs.roi,
                                             dir_path=self.inputs.dir_path,
                                             ID=self.inputs.ID,
                                             network=self.inputs.network,
                                             smooth=self.inputs.smooth,
                                             atlas=self.inputs.atlas,
                                             uatlas=self.inputs.uatlas,
                                             labels=self.inputs.labels,
                                             c_boot=self.inputs.c_boot,
                                             block_size=self.inputs.block_size,
                                             hpass=self.inputs.hpass,
                                             mask=out_name_mask)

        te.prepare_inputs()
        if self.inputs.parc is False:
            if len(self.inputs.coords) > 0:
                te.extract_ts_coords()
            else:
                raise RuntimeError(
                    '\nERROR: Cannot extract time-series from an empty list of coordinates. \nThis usually means '
                    'that no nodes were generated based on the specified conditions at runtime (e.g. atlas was '
                    'overly restricted by an RSN or some user-defined mask.')
        else:
            te.extract_ts_parc()

        if float(self.inputs.c_boot) > 0:
            te.bootstrap_timeseries()

        te.save_and_cleanup()

        self._results['ts_within_nodes'] = te.ts_within_nodes
        self._results['node_size'] = te.node_size
        self._results['smooth'] = te.smooth
        self._results['dir_path'] = te.dir_path
        self._results['atlas'] = te.atlas
        self._results['uatlas'] = te.uatlas
        self._results['labels'] = te.labels
        self._results['coords'] = te.coords
        self._results['c_boot'] = te.c_boot
        self._results['hpass'] = te.hpass
        self._results['roi'] = self.inputs.roi

        del te
        gc.collect()

        return runtime


class _PlotStructInputSpec(BaseInterfaceInputSpec):
    """Input interface wrapper for PlotStruct"""
    conn_matrix = traits.Array(mandatory=True)
    conn_model = traits.Str(mandatory=True)
    atlas = traits.Any()
    dir_path = Directory(exists=True, mandatory=True)
    ID = traits.Any(mandatory=True)
    network = traits.Any()
    labels = traits.Array(mandatory=True)
    roi = traits.Any()
    coords = traits.Array(mandatory=True)
    thr = traits.Any()
    node_size = traits.Any()
    edge_threshold = traits.Any()
    prune = traits.Any()
    uatlas = traits.Any()
    target_samples = traits.Any()
    norm = traits.Any()
    binary = traits.Bool()
    track_type = traits.Any()
    directget = traits.Any()
    min_length = traits.Any()


class _PlotStructOutputSpec(BaseInterfaceInputSpec):
    """Output interface wrapper for PlotStruct"""
    out = traits.Str


class PlotStruct(SimpleInterface):
    """Interface wrapper for PlotStruct"""
    input_spec = _PlotStructInputSpec
    output_spec = _PlotStructOutputSpec

    def _run_interface(self, runtime):
        from pynets.plotting import plot_gen
        if self.inputs.coords.ndim == 1:
            print('Only 1 node detected. Plotting is not applicable...')
        else:
            plot_gen.plot_all_struct(self.inputs.conn_matrix,
                                     self.inputs.conn_model,
                                     self.inputs.atlas,
                                     self.inputs.dir_path,
                                     self.inputs.ID,
                                     self.inputs.network,
                                     self.inputs.labels.tolist(),
                                     self.inputs.roi,
                                     [tuple(coord) for coord in self.inputs.coords.tolist()],
                                     self.inputs.thr,
                                     self.inputs.node_size,
                                     self.inputs.edge_threshold,
                                     self.inputs.prune,
                                     self.inputs.uatlas,
                                     self.inputs.target_samples,
                                     self.inputs.norm,
                                     self.inputs.binary,
                                     self.inputs.track_type,
                                     self.inputs.directget,
                                     self.inputs.min_length)

        self._results['out'] = 'None'

        return runtime


class _PlotFuncInputSpec(BaseInterfaceInputSpec):
    """Input interface wrapper for PlotFunc"""
    conn_matrix = traits.Array(mandatory=True)
    conn_model = traits.Str(mandatory=True)
    atlas = traits.Any()
    dir_path = Directory(exists=True, mandatory=True)
    ID = traits.Any(mandatory=True)
    network = traits.Any()
    labels = traits.Array(mandatory=True)
    roi = traits.Any()
    coords = traits.Array(mandatory=True)
    thr = traits.Any()
    node_size = traits.Any()
    edge_threshold = traits.Any()
    smooth = traits.Any()
    prune = traits.Any()
    uatlas = traits.Any()
    c_boot = traits.Any()
    norm = traits.Any()
    binary = traits.Bool()
    hpass = traits.Any()


class _PlotFuncOutputSpec(BaseInterfaceInputSpec):
    """Output interface wrapper for PlotFunc"""
    out = traits.Str


class PlotFunc(SimpleInterface):
    """Interface wrapper for PlotFunc"""
    input_spec = _PlotFuncInputSpec
    output_spec = _PlotFuncOutputSpec

    def _run_interface(self, runtime):
        from pynets.plotting import plot_gen

        if self.inputs.coords.ndim == 1:
            print('Only 1 node detected. Plotting is not applicable...')
        else:
            plot_gen.plot_all_func(self.inputs.conn_matrix,
                                   self.inputs.conn_model,
                                   self.inputs.atlas,
                                   self.inputs.dir_path,
                                   self.inputs.ID,
                                   self.inputs.network,
                                   self.inputs.labels.tolist(),
                                   self.inputs.roi,
                                   [tuple(coord) for coord in self.inputs.coords.tolist()],
                                   self.inputs.thr,
                                   self.inputs.node_size,
                                   self.inputs.edge_threshold,
                                   self.inputs.smooth,
                                   self.inputs.prune,
                                   self.inputs.uatlas,
                                   self.inputs.c_boot,
                                   self.inputs.norm,
                                   self.inputs.binary,
                                   self.inputs.hpass)

        self._results['out'] = 'None'

        return runtime


class _RegisterDWIInputSpec(BaseInterfaceInputSpec):
    """Input interface wrapper for RegisterDWI"""
    fa_path = File(exists=True, mandatory=True)
    ap_path = File(exists=True, mandatory=True)
    B0_mask = File(exists=True, mandatory=True)
    anat_file = File(exists=True, mandatory=True)
    gtab_file = File(exists=True, mandatory=True)
    dwi_file = File(exists=True, mandatory=True)
    vox_size = traits.Str('2mm', mandatory=True, usedefault=True)
    waymask = traits.Any(mandatory=False)
    mask = traits.Any(mandatory=False)
    simple = traits.Bool(False, usedefault=True)
    overwrite = traits.Bool(True, usedefault=True)


class _RegisterDWIOutputSpec(TraitedSpec):
    """Output interface wrapper for RegisterDWI"""
    wm_in_dwi = File(exists=True, mandatory=True)
    gm_in_dwi = File(exists=True, mandatory=True)
    vent_csf_in_dwi = File(exists=True, mandatory=True)
    csf_mask_dwi = File(exists=True, mandatory=True)
    anat_file = File(exists=True, mandatory=True)
    B0_mask = File(exists=True, mandatory=True)
    ap_path = File(exists=True, mandatory=True)
    gtab_file = File(exists=True, mandatory=True)
    dwi_file = File(exists=True, mandatory=True)
    waymask_in_dwi = traits.Any(mandatory=False)
    basedir_path = Directory(exists=True, mandatory=True)
    t1w2dwi = File(exists=True, mandatory=True)

class RegisterDWI(SimpleInterface):
    """Interface wrapper for RegisterDWI to create T1w->MNI->DWI mappings."""
    input_spec = _RegisterDWIInputSpec
    output_spec = _RegisterDWIOutputSpec

    def _run_interface(self, runtime):
        import gc
        import os.path as op
        from pynets.registration import register
        from nipype.utils.filemanip import fname_presuffix, copyfile

        anat_file_tmp_path = fname_presuffix(self.inputs.anat_file, suffix='_tmp', newpath=runtime.cwd)
        copyfile(self.inputs.anat_file, anat_file_tmp_path, copy=True, use_hardlink=False)

        fa_tmp_path = fname_presuffix(self.inputs.fa_path, suffix='_tmp', newpath=runtime.cwd)
        copyfile(self.inputs.fa_path, fa_tmp_path, copy=True, use_hardlink=False)

        ap_tmp_path = fname_presuffix(self.inputs.ap_path, suffix='_tmp', newpath=runtime.cwd)
        copyfile(self.inputs.ap_path, ap_tmp_path, copy=True, use_hardlink=False)

        B0_mask_tmp_path = fname_presuffix(self.inputs.B0_mask, suffix='_tmp', newpath=runtime.cwd)
        copyfile(self.inputs.B0_mask, B0_mask_tmp_path, copy=True, use_hardlink=False)

        reg = register.DmriReg(basedir_path=runtime.cwd,
                               fa_path=fa_tmp_path,
                               ap_path=ap_tmp_path,
                               B0_mask=B0_mask_tmp_path,
                               anat_file=anat_file_tmp_path,
                               mask=self.inputs.mask,
                               vox_size=self.inputs.vox_size,
                               simple=self.inputs.simple)

        if (self.inputs.overwrite is True) or (op.isfile(reg.map_path) is False):
            # Perform anatomical segmentation
            reg.gen_tissue()

        if (self.inputs.overwrite is True) or (op.isfile(reg.t1w2dwi) is False):
            # Align t1w to dwi
            reg.t1w2dwi_align()

        if (self.inputs.overwrite is True) or (op.isfile(reg.wm_gm_int_in_dwi) is False):
            # Align tissue
            reg.tissue2dwi_align()

        if self.inputs.waymask is not None:
            if (self.inputs.overwrite is True) or (op.isfile(reg.waymask_in_dwi) is False):
                # Align waymask
                reg.waymask2dwi_align(self.inputs.waymask)
        else:
            reg.waymask_in_dwi = None

        self._results['wm_in_dwi'] = reg.wm_in_dwi
        self._results['gm_in_dwi'] = reg.gm_in_dwi
        self._results['vent_csf_in_dwi'] = reg.vent_csf_in_dwi
        self._results['csf_mask_dwi'] = reg.csf_mask_dwi
        self._results['anat_file'] = self.inputs.anat_file
        self._results['t1w2dwi'] = reg.t1w2dwi
        self._results['B0_mask'] = self.inputs.B0_mask
        self._results['ap_path'] = self.inputs.ap_path
        self._results['gtab_file'] = self.inputs.gtab_file
        self._results['dwi_file'] = self.inputs.dwi_file
        self._results['waymask_in_dwi'] = reg.waymask_in_dwi
        self._results['basedir_path'] = runtime.cwd

        gc.collect()

        return runtime


class _RegisterFuncInputSpec(BaseInterfaceInputSpec):
    """Input interface wrapper for RegisterFunc"""
    anat_file = File(exists=True, mandatory=True)
    mask = traits.Any(mandatory=False)
    vox_size = traits.Str('2mm', mandatory=True, usedefault=True)
    simple = traits.Bool(False, usedefault=True)
    overwrite = traits.Bool(True, usedefault=True)


class _RegisterFuncOutputSpec(TraitedSpec):
    """Output interface wrapper for RegisterFunc"""
    reg_fmri_complete = traits.Bool()
    basedir_path = Directory(exists=True, mandatory=True)


class RegisterFunc(SimpleInterface):
    """Interface wrapper for RegisterDWI to create Func->T1w->MNI mappings."""
    input_spec = _RegisterFuncInputSpec
    output_spec = _RegisterFuncOutputSpec

    def _run_interface(self, runtime):
        import gc
        import os.path as op
        from pynets.registration import register
        from nipype.utils.filemanip import fname_presuffix, copyfile

        # anat_file_tmp_path = fname_presuffix(self.inputs.anat_file, suffix='_tmp', newpath=runtime.cwd)
        # copyfile(self.inputs.anat_file, anat_file_tmp_path, copy=True, use_hardlink=False)
        if self.inputs.mask:
            mask_tmp_path = fname_presuffix(self.inputs.mask, suffix='_tmp', newpath=runtime.cwd)
            copyfile(self.inputs.mask, mask_tmp_path, copy=True, use_hardlink=False)
        else:
            mask_tmp_path = None

        reg = register.FmriReg(basedir_path=runtime.cwd,
                               anat_file=self.inputs.anat_file,
                               mask=mask_tmp_path,
                               vox_size=self.inputs.vox_size,
                               simple=self.inputs.simple)

        if (self.inputs.overwrite is True) or (op.isfile(reg.map_path) is False):
            # Perform anatomical segmentation
            reg.gen_tissue()

        if (self.inputs.overwrite is True) or (op.isfile(reg.t1_aligned_mni) is False):
            # Align t1w to dwi
            reg.t1w2mni_align()

        self._results['reg_fmri_complete'] = True
        self._results['basedir_path'] = runtime.cwd

        gc.collect()

        return runtime


class _TrackingInputSpec(BaseInterfaceInputSpec):
    """Input interface wrapper for Tracking"""
    B0_mask = File(exists=True, mandatory=True)
    gm_in_dwi = File(exists=True, mandatory=True)
    vent_csf_in_dwi = File(exists=True, mandatory=True)
    wm_in_dwi = File(exists=True, mandatory=True)
    tiss_class = traits.Str(mandatory=True)
    labels_im_file_wm_gm_int = File(exists=True, mandatory=True)
    labels_im_file = File(exists=True, mandatory=True)
    target_samples = traits.Any(mandatory=True)
    curv_thr_list = traits.List(mandatory=True)
    step_list = traits.List(mandatory=True)
    track_type = traits.Str(mandatory=True)
    min_length = traits.Any(mandatory=True)
    maxcrossing = traits.Any(mandatory=True)
    directget = traits.Str(mandatory=True)
    conn_model = traits.Str(mandatory=True)
    gtab_file = File(exists=True, mandatory=True)
    dwi_file = File(exists=True, mandatory=True)
    network = traits.Any(mandatory=False)
    node_size = traits.Any()
    dens_thresh = traits.Bool()
    ID = traits.Any(mandatory=True)
    roi = traits.Any(mandatory=False)
    min_span_tree = traits.Bool()
    disp_filt = traits.Bool()
    parc = traits.Bool()
    prune = traits.Any()
    atlas = traits.Any(mandatory=True)
    uatlas = traits.Any(mandatory=False)
    labels = traits.Any(mandatory=True)
    coords = traits.Any(mandatory=True)
    norm = traits.Any()
    binary = traits.Bool(False, usedefault=True)
    atlas_mni = File(exists=True, mandatory=True)
    fa_path = File(exists=True, mandatory=True)
    waymask = traits.Any(mandatory=False)
    t1w2dwi = File(exists=True, mandatory=True)
    roi_neighborhood_tol = traits.Any(8, mandatory=True, usedefault=True)
    sphere = traits.Str('repulsion724', mandatory=True, usedefault=True)


class _TrackingOutputSpec(TraitedSpec):
    """Output interface wrapper for Tracking"""
    streams = File(exists=True, mandatory=True)
    track_type = traits.Str(mandatory=True)
    target_samples = traits.Any(mandatory=True)
    conn_model = traits.Str(mandatory=True)
    dir_path = traits.Any()
    network = traits.Any(mandatory=False)
    node_size = traits.Any()
    dens_thresh = traits.Bool()
    ID = traits.Any(mandatory=True)
    roi = traits.Any(mandatory=False)
    min_span_tree = traits.Bool()
    disp_filt = traits.Bool()
    parc = traits.Bool()
    prune = traits.Any()
    atlas = traits.Any(mandatory=True)
    uatlas = traits.Any(mandatory=False)
    labels = traits.Any(mandatory=True)
    coords = traits.Any(mandatory=True)
    norm = traits.Any()
    binary = traits.Bool(False, usedefault=True)
    atlas_mni = File(exists=True, mandatory=True)
    curv_thr_list = traits.List(mandatory=True)
    step_list = traits.List(mandatory=True)
    fa_path = File(exists=True, mandatory=True)
    dm_path = File(exists=True, mandatory=True)
    directget = traits.Str(mandatory=True)
    labels_im_file = File(exists=True, mandatory=True)
    roi_neighborhood_tol = traits.Any()
    min_length = traits.Any()


class Tracking(SimpleInterface):
    """Interface wrapper for Tracking"""
    input_spec = _TrackingInputSpec
    output_spec = _TrackingOutputSpec

    def _run_interface(self, runtime):
        import gc
        import numpy as np
        import nibabel as nib
        try:
            import cPickle as pickle
        except ImportError:
            import _pickle as pickle
        from dipy.io import load_pickle
        from colorama import Fore, Style
        from dipy.data import get_sphere
        from pynets.core import utils
        from pynets.dmri.track import prep_tissues, reconstruction, create_density_map, track_ensemble

        # Load diffusion data
        dwi_img = nib.load(self.inputs.dwi_file)

        # Fit diffusion model
        mod_fit = reconstruction(self.inputs.conn_model, load_pickle(self.inputs.gtab_file),
                                 np.asarray(dwi_img.dataobj), self.inputs.B0_mask)

        # Load atlas parcellation (and its wm-gm interface reduced version for seeding)
        atlas_data = np.array(nib.load(self.inputs.labels_im_file).dataobj).astype('uint16')
        atlas_data_wm_gm_int = np.asarray(nib.load(self.inputs.labels_im_file_wm_gm_int).dataobj).astype('uint16')

        # Build mask vector from atlas for later roi filtering
        parcels = []
        i = 0
        for roi_val in np.unique(atlas_data)[1:]:
            parcels.append(atlas_data == roi_val)
            i = i + 1

        if np.sum(atlas_data) == 0:
            raise ValueError(
                'ERROR: No non-zero voxels found in atlas. Check any roi masks and/or wm-gm interface images '
                'to verify overlap with dwi-registered atlas.')

        # Iteratively build a list of streamlines for each ROI while tracking
        print("%s%s%s%s" % (Fore.GREEN, 'Target number of samples: ', Fore.BLUE, self.inputs.target_samples))
        print(Style.RESET_ALL)
        print("%s%s%s%s" % (Fore.GREEN, 'Using curvature threshold(s): ', Fore.BLUE, self.inputs.curv_thr_list))
        print(Style.RESET_ALL)
        print("%s%s%s%s" % (Fore.GREEN, 'Using step size(s): ', Fore.BLUE, self.inputs.step_list))
        print(Style.RESET_ALL)
        print("%s%s%s%s" % (Fore.GREEN, 'Tracking type: ', Fore.BLUE, self.inputs.track_type))
        print(Style.RESET_ALL)
        if self.inputs.directget == 'prob':
            print("%s%s%s%s" % (Fore.GREEN, 'Direction-getting type: ', Fore.BLUE, 'Probabilistic'))
        elif self.inputs.directget == 'boot':
            print("%s%s%s%s" % (Fore.GREEN, 'Direction-getting type: ', Fore.BLUE, 'Bootstrapped'))
        elif self.inputs.directget == 'closest':
            print("%s%s%s%s" % (Fore.GREEN, 'Direction-getting type: ', Fore.BLUE, 'Closest Peak'))
        elif self.inputs.directget == 'det':
            print("%s%s%s%s" % (Fore.GREEN, 'Direction-getting type: ', Fore.BLUE, 'Deterministic Maximum'))
        else:
            raise ValueError('Direction-getting type not recognized!')
        print(Style.RESET_ALL)

        # Commence Ensemble Tractography
        streamlines = track_ensemble(np.asarray(dwi_img.dataobj), self.inputs.target_samples, atlas_data_wm_gm_int,
                                     parcels, mod_fit,
                                     prep_tissues(self.inputs.t1w2dwi, self.inputs.gm_in_dwi,
                                                  self.inputs.vent_csf_in_dwi, self.inputs.wm_in_dwi,
                                                  self.inputs.tiss_class),
                                     get_sphere(self.inputs.sphere), self.inputs.directget, self.inputs.curv_thr_list,
                                     self.inputs.step_list, self.inputs.track_type, self.inputs.maxcrossing,
                                     int(self.inputs.roi_neighborhood_tol), self.inputs.min_length, self.inputs.waymask)

        # Create streamline density map
        [streams, dir_path, dm_path] = create_density_map(dwi_img, utils.do_dir_path(self.inputs.atlas,
                                                                                     self.inputs.dwi_file), streamlines,
                                                          self.inputs.conn_model, self.inputs.target_samples,
                                                          self.inputs.node_size, self.inputs.curv_thr_list,
                                                          self.inputs.step_list, self.inputs.network, self.inputs.roi,
                                                          self.inputs.directget, self.inputs.min_length)

        self._results['streams'] = streams
        self._results['track_type'] = self.inputs.track_type
        self._results['target_samples'] = self.inputs.target_samples
        self._results['conn_model'] = self.inputs.conn_model
        self._results['dir_path'] = dir_path
        self._results['network'] = self.inputs.network
        self._results['node_size'] = self.inputs.node_size
        self._results['dens_thresh'] = self.inputs.dens_thresh
        self._results['ID'] = self.inputs.ID
        self._results['roi'] = self.inputs.roi
        self._results['min_span_tree'] = self.inputs.min_span_tree
        self._results['disp_filt'] = self.inputs.disp_filt
        self._results['parc'] = self.inputs.parc
        self._results['prune'] = self.inputs.prune
        self._results['atlas'] = self.inputs.atlas
        self._results['uatlas'] = self.inputs.uatlas
        self._results['labels'] = self.inputs.labels
        self._results['coords'] = self.inputs.coords
        self._results['norm'] = self.inputs.norm
        self._results['binary'] = self.inputs.binary
        self._results['atlas_mni'] = self.inputs.atlas_mni
        self._results['curv_thr_list'] = self.inputs.curv_thr_list
        self._results['step_list'] = self.inputs.step_list
        self._results['fa_path'] = self.inputs.fa_path
        self._results['dm_path'] = dm_path
        self._results['directget'] = self.inputs.directget
        self._results['labels_im_file'] = self.inputs.labels_im_file
        self._results['roi_neighborhood_tol'] = self.inputs.roi_neighborhood_tol
        self._results['min_length'] = self.inputs.min_length

        del streamlines, atlas_data_wm_gm_int, atlas_data, mod_fit, parcels
        dwi_img.uncache()
        gc.collect()

        return runtime
