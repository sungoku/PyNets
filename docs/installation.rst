.. include:: links.rst

------------
Installation
------------

There are three ways to use pynets: in a `Docker Container`_,
in a `Singularity Container`_, or in a `Manually
Prepared Environment (Python 3.5+)`_.
Using a local container method is highly recommended.
Once you are ready to run pynets, see Usage_ for details.

Docker Container
================

In order to run pynets in a Docker container, Docker must be `installed
<https://docs.docker.com/engine/installation/>`_.
Once Docker is installed, you can build a container and test it interactively as follows: ::

    BUILDIR=$(pwd)
    mkdir -p ${BUILDIR}/pynets_images
    docker build -t pynets .

    docker run -ti --rm --privileged \
        --entrypoint /bin/bash
        -v /tmp:/tmp \
        -v /var/tmp:/var/tmp \
        -v /input_files_local:/inputs \
        pynets

See `External Dependencies`_ for more information (e.g., specific versions) on what is included in the latest Docker images.


Singularity Container
=====================

For security reasons, many HPCs (e.g., TACC) do not allow Docker containers, but do
allow `Singularity <https://github.com/singularityware/singularity>`_ containers.

Preparing a Singularity image (Singularity version >= 2.5)
----------------------------------------------------------
If the version of Singularity on your HPC is modern enough you can create Singularity
image directly on the HCP.
This is as simple as: ::

    $ singularity build /my_images/pynets-<version>.simg docker://dpys/pynets:<version>

Where ``<version>`` should be replaced with the desired version of PyNets that you want to download.


Preparing a Singularity image (Singularity version < 2.5)
---------------------------------------------------------
In this case, start with a machine (e.g., your personal computer) with Docker installed.
Use `docker2singularity <https://github.com/singularityware/docker2singularity>`_ to
create a singularity image.
You will need an active internet connection and some time. ::

    $ docker run --privileged -t --rm \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v D:\host\path\where\to\output\singularity\image:/output \
        singularityware/docker2singularity \
        dpys/pynets:<version>

Where ``<version>`` should be replaced with the desired version of PyNets that you want
to download.

Beware of the back slashes, expected for Windows systems.
For \*nix users the command translates as follows: ::

    $ docker run --privileged -t --rm \
        -V /var/run/docker.sock:/var/run/docker.sock \
        -v /absolute/path/to/output/folder:/output \
        singularityware/docker2singularity \
        dpys/pynets:<version>

Transfer the resulting Singularity image to the HPC, for example, using ``scp``. ::

    $ scp pynets*.img user@hcpserver.edu:/my_images

Running a Singularity Image
---------------------------

If the data to be preprocessed is also on the HPC, you are ready to run pynets. ::

    $ singularity run -w \
     /scratch/04171/dpisner/pynets_singularity_latest-2020-02-07-eccf145ea766.img \
     -p 1 -mod 'partcorr' 'corr' -min_thr 0.20 -max_thr 1.00 -step_thr 0.10 -sm 0 2 4 -hp 0 0.028 0.080 -ct 'ward' \
     -k 100 200 -pm "24,48" \
     -b 100 -bs 12 -norm 6 -cc 'tcorr' \
     -cm '/outputs/triple_net_ICA_overlap_3_sig_bin.nii.gz' \
     -anat "/inputs/sub-"$PARTIC"/ses-"$ses"/anat/sub-"$PARTIC"_space-MNI152NLin2009cAsym_desc-preproc_T1w_brain.nii.gz" \
     -func "/inputs/sub-"$PARTIC"/ses-"$ses"/func/sub-"$PARTIC"_ses-"$ses"_task-rest_space-MNI152NLin2009cAsym_desc-smoothAROMAnonaggr_bold_masked.nii.gz" \
     -conf "/inputs/sub-"$PARTIC"/ses-"$ses"/func/sub-"$PARTIC"_ses-"$ses"_task-rest_desc-confounds_regressors.tsv" \
     -m "/inputs/sub-"$PARTIC"/ses-"$ses"/func/sub-"$PARTIC"_ses-"$ses"_task-rest_space-MNI152NLin2009cAsym_desc-brain_mask.nii.gz" \
     -id ""$PARTIC"_run"$ses"" -plug 'MultiProc' -work '/tmp'

.. note::

   Singularity by default `exposes all environment variables from the host inside
   the container <https://github.com/singularityware/singularity/issues/445>`_.
   Because of this your host libraries (such as nipype) could be accidentally used
   instead of the ones inside the container - if they are included in ``PYTHONPATH``.
   To avoid such situation we recommend using the ``--cleanenv`` singularity flag
   in production use. For example: ::

      $ singularity run --no-home --cleanenv ~/pynets_latest-2016-12-04-5b74ad9a4c4d.img \
        -p 1 -mod 'partcorr' 'corr' -min_thr 0.20 -max_thr 1.00 -step_thr 0.10 -sm 0 2 4 -hp 0 0.028 0.080 -ct 'ward' \
        -k 100 200 -pm "24,48" \
        -b 100 -bs 12 -norm 6 -cc 'tcorr' \
        -cm '/outputs/triple_net_ICA_overlap_3_sig_bin.nii.gz' \
        -anat "/inputs/sub-"$PARTIC"/ses-"$ses"/anat/sub-"$PARTIC"_space-MNI152NLin2009cAsym_desc-preproc_T1w_brain.nii.gz" \
        -func "/inputs/sub-"$PARTIC"/ses-"$ses"/func/sub-"$PARTIC"_ses-"$ses"_task-rest_space-MNI152NLin2009cAsym_desc-smoothAROMAnonaggr_bold_masked.nii.gz" \
        -conf "/inputs/sub-"$PARTIC"/ses-"$ses"/func/sub-"$PARTIC"_ses-"$ses"_task-rest_desc-confounds_regressors.tsv" \
        -m "/inputs/sub-"$PARTIC"/ses-"$ses"/func/sub-"$PARTIC"_ses-"$ses"_task-rest_space-MNI152NLin2009cAsym_desc-brain_mask.nii.gz" \
        -id ""$PARTIC"_run"$ses"" -plug 'MultiProc' -work '/tmp'

   or, unset the ``PYTHONPATH`` variable before running: ::

      $ unset PYTHONPATH; singularity run ~/pynets_latest-2016-12-04-5b74ad9a4c4d.img \
        -p 1 -mod 'partcorr' 'corr' -min_thr 0.20 -max_thr 1.00 -step_thr 0.10 -sm 0 2 4 -hp 0 0.028 0.080 -ct 'ward' \
        -k 100 200 -pm "24,48" \
        -b 100 -bs 12 -norm 6 -cc 'tcorr' \
        -cm '/outputs/triple_net_ICA_overlap_3_sig_bin.nii.gz' \
        -anat "/inputs/sub-"$PARTIC"/ses-"$ses"/anat/sub-"$PARTIC"_space-MNI152NLin2009cAsym_desc-preproc_T1w_brain.nii.gz" \
        -func "/inputs/sub-"$PARTIC"/ses-"$ses"/func/sub-"$PARTIC"_ses-"$ses"_task-rest_space-MNI152NLin2009cAsym_desc-smoothAROMAnonaggr_bold_masked.nii.gz" \
        -conf "/inputs/sub-"$PARTIC"/ses-"$ses"/func/sub-"$PARTIC"_ses-"$ses"_task-rest_desc-confounds_regressors.tsv" \
        -m "/inputs/sub-"$PARTIC"/ses-"$ses"/func/sub-"$PARTIC"_ses-"$ses"_task-rest_space-MNI152NLin2009cAsym_desc-brain_mask.nii.gz" \
        -id ""$PARTIC"_run"$ses"" -plug 'MultiProc' -work '/tmp'

.. note::

   Depending on how Singularity is configured on your cluster it might or might not
   automatically bind (mount or expose) host folders to the container.
   If this is not done automatically you will need to bind the necessary folders using
   the ``-B <host_folder>:<container_folder>`` Singularity argument.
   For example: ::

      $ singularity run --cleanenv -B /work:/work ~/pynets_latest-2016-12-04-5b74ad9a4c4d.img \
        -B /scratch/04171/dpisner/pynets_out:/inputs,/scratch/04171/dpisner/masks/"$PARTIC"_triple_network_masks_"$ses":/outputs \
        -p 1 -mod 'partcorr' 'corr' -min_thr 0.20 -max_thr 1.00 -step_thr 0.10 -sm 0 2 4 -hp 0 0.028 0.080 -ct 'ward' \
        -k 100 200 -pm "24,48" \
        -b 100 -bs 12 -norm 6 -cc 'tcorr' \
        -cm '/outputs/triple_net_ICA_overlap_3_sig_bin.nii.gz' \
        -anat "/inputs/sub-"$PARTIC"/ses-"$ses"/anat/sub-"$PARTIC"_space-MNI152NLin2009cAsym_desc-preproc_T1w_brain.nii.gz" \
        -func "/inputs/sub-"$PARTIC"/ses-"$ses"/func/sub-"$PARTIC"_ses-"$ses"_task-rest_space-MNI152NLin2009cAsym_desc-smoothAROMAnonaggr_bold_masked.nii.gz" \
        -conf "/inputs/sub-"$PARTIC"/ses-"$ses"/func/sub-"$PARTIC"_ses-"$ses"_task-rest_desc-confounds_regressors.tsv" \
        -m "/inputs/sub-"$PARTIC"/ses-"$ses"/func/sub-"$PARTIC"_ses-"$ses"_task-rest_space-MNI152NLin2009cAsym_desc-brain_mask.nii.gz" \
        -id ""$PARTIC"_run"$ses"" -plug 'MultiProc' -work '/tmp'

Manually Prepared Environment (Python 3.5+)
===========================================

.. warning::

   This method is not recommended! Make sure you would rather do this than
   use a `Docker Container`_ or a `Singularity Container`_.

Make sure all of pynets's `External Dependencies`_ are installed.
These tools must be installed and their binaries available in the
system's ``$PATH``.
A relatively interpretable description of how your environment can be set-up
is found in the `Dockerfile <https://github.com/dPys/PyNets/blob/master/Dockerfile>`_.

On a functional Python 3.5 (or above) environment with ``pip`` installed,
PyNets can be installed using the habitual command ::

    $ pip install pynets


External Dependencies
---------------------

PyNets is written using Python 3.5 (or above), and is based on
nipype_.

PyNets requires some other neuroimaging software tools that are
not handled by the Python's packaging system (Pypi) used to deploy
the ``pynets`` package:

- FSL_ (version >=5.0.9)
