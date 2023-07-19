import sima
import sima.motion
from sima.motion import HiddenMarkov2D
import numpy as np
import os
import pickle
import h5py
import shutil

def fill_gaps(framenumber, sequence, frame_iter1):  # adapted from SIMA source code/Vijay Namboodiri
    first_obs = next(frame_iter1)
    for frame in frame_iter1:
        for frame_chan, fobs_chan in zip(frame, first_obs):
            fobs_chan[np.isnan(fobs_chan)] = frame_chan[np.isnan(fobs_chan)]
        if all(np.all(np.isfinite(chan)) for chan in first_obs):
            break
    most_recent = [x * np.nan for x in first_obs]
    while True:
        frame = np.array(sequence[framenumber])[0, :, :, :, :]
        for fr_chan, mr_chan in zip(frame, most_recent):
            mr_chan[np.isfinite(fr_chan)] = fr_chan[np.isfinite(fr_chan)]
        temp = [np.nan_to_num(mr_ch) + np.isnan(mr_ch) * fo_ch
                for mr_ch, fo_ch in zip(most_recent, first_obs)]
        framenumber = yield np.array(temp)[0, :, :, 0]

# define file path and name
filename = 'VJ_OFCVTA_7_260_D6_offset'

folder = r'C:\Users\Eesha\Documents\GitHub\sima_visualization\generated\\'

tif_h5 = 1 # USER DEFINE: 0 for tiff, 1 for h5

segment_file = 'VJ_OFCVTA_7_260_D6_offset_mc.sima' #'VJ_OFC_6_D6.sima'
segment_dir = 'C:\\Users\\Eesha\\Documents\\GitHub\\sima_visualization\\generated\\'
segment_path = os.path.join(segment_dir, segment_file)

def run():
    global sima
    # get full path of file and load via sima

    if tif_h5 == 0:
        
        # splices file and file directory into a single path for loading
        datafile = os.path.join(folder, '%s.tif'%filename)
        # sequence: object that contains record of whole dataset; data not stored into memory all at once
        sequences = [sima.Sequence.create('TIFF', datafile)] 
        
    elif tif_h5 == 1:
        
        datafile = os.path.join(folder, '%s.h5'%filename)
        sequences = [sima.Sequence.create('HDF5', datafile, 'tyx')]

    mc_approach = sima.motion.HiddenMarkov2D(granularity='row', max_displacement=[10, 10], n_processes = 1, verbose=True)

    dataset, rows, columns = mc_approach.correct(sequences, os.path.join(folder, filename + '_mc.sima'), channel_names=['GCaMP'])

    """calculate trim dimensions (ie. sima will cut out x and y columns that 
    are missing data due to shifts from motion correction) """

    row_slice = [rows.start, rows.stop]
    column_slice = [columns.start, columns.stop]

    hf = h5py.File( folder + filename + '_trim_dims.h5', 'w')
    hf.create_dataset('rows', data=row_slice)
    hf.create_dataset('columns', data=column_slice)
    hf.close()

    dataset = sima.ImagingDataset.load(os.path.join(folder, filename + '_mc.sima'))
    sequence_data = dataset.sequences[0]

    data_to_save = np.empty([dataset.num_frames, dataset.frame_shape[1], dataset.frame_shape[2]])
    frame_iter1 = iter(sequence_data)

    fill_gapscaller = fill_gaps(0, sequence_data, frame_iter1)
    fill_gapscaller.send(None)

    for frame_num in range(dataset.num_frames):
        data_to_save[frame_num, ...] = fill_gapscaller.send(frame_num).astype('uint8')

    sima_mc_bidi_outpath = os.path.join(folder, filename + '_sima_mc_.h5')
    h5_write_bidi_corr = h5py.File(sima_mc_bidi_outpath, 'w')
    h5_write_bidi_corr.create_dataset('imaging', data=data_to_save.astype('uint8'))
    h5_write_bidi_corr.close()

    # load pickled/saved motion-corrected data

    file = open( os.path.join(folder, filename + '_mc.sima/sequences.pkl') , 'rb')
    sequences = pickle.load(file)
    file.close()

    dataset = sima.ImagingDataset.load( os.path.join(folder, filename + '_mc.sima') )
    # data dimensions are: plane, row, column, channel

    # show motion displacements after motion correction
    mcDisp_approach = sima.motion.HiddenMarkov2D(granularity='row', max_displacement=[30, 30], n_processes = 1, verbose=True)

    displacements = mcDisp_approach.estimate(dataset)

    # save the resulting displacement file
    displacement_file = open( os.path.join(folder, filename + '_mc.sima/displacement.pkl'), "wb" )
    pickle.dump( displacements, displacement_file )
    displacement_file.close()

    # process and save np array of composite displacement
    data_dims = displacements[0].shape
    disp_np = np.squeeze( np.array(displacements[0]) )
    disp_meanpix = np.mean( disp_np, axis=1 ) # avg across lines (y axis)

    sima_disp = np.sqrt( np.square(disp_meanpix[:,0]) + np.square(disp_meanpix[:,1]) ) # calculate composite x + y offsets
    np.save(segment_dir + 'displacements\\displacements_sima.npy', sima_disp)

    import sima.segment
    stica_approach = sima.segment.STICA(components=5)
    stica_approach.append(sima.segment.SparseROIsFromMasks())
    stica_approach.append(sima.segment.SmoothROIBoundaries())
    stica_approach.append(sima.segment.MergeOverlapping(threshold=0.5))

    dataset = sima.ImagingDataset.load(segment_path)
    rois = dataset.segment(stica_approach, 'auto_ROIs')

    import matplotlib.pyplot as plt

    np.array( rois[0].mask[0][0] )

    #plt.imshow(rois[0].mask)

    dataset.extract(signal_channel='GCaMP', label='GCaMP_signals', n_processes=16) # 16 processes: 5 min 19 s

    dataset.export_signals(segment_path + '_example_signals.csv')