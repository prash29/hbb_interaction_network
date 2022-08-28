import argparse
import glob

import numpy as np
# import setGPU  # noqa: F401
import torch
import tqdm
from sklearn.metrics import accuracy_score, roc_auc_score
from scipy.special import softmax
import onnx
import onnxruntime as ort

N = 60  # number of charged particles
N_sv = 5  # number of SVs
N_neu = 100
n_targets = 2  # number of classes
save_path_test = "//grand/RAPINS/ruike/new_hbb/test/"#"dataset/test/"
# save_path_train_val = "dataset/train/"

spectators = [
    "fj_pt",
    "fj_eta",
    "fj_sdmass",
    "fj_n_sdsubjets",
    "fj_doubleb",
    "fj_tau21",
    "fj_tau32",
    "npv",
    "npfcands",
    "ntracks",
    "nsv",
]

params_0 = [
    "fj_jetNTracks",
    "fj_nSV",
    "fj_tau0_trackEtaRel_0",
    "fj_tau0_trackEtaRel_1",
    "fj_tau0_trackEtaRel_2",
    "fj_tau1_trackEtaRel_0",
    "fj_tau1_trackEtaRel_1",
    "fj_tau1_trackEtaRel_2",
    "fj_tau_flightDistance2dSig_0",
    "fj_tau_flightDistance2dSig_1",
    "fj_tau_vertexDeltaR_0",
    "fj_tau_vertexEnergyRatio_0",
    "fj_tau_vertexEnergyRatio_1",
    "fj_tau_vertexMass_0",
    "fj_tau_vertexMass_1",
    "fj_trackSip2dSigAboveBottom_0",
    "fj_trackSip2dSigAboveBottom_1",
    "fj_trackSip2dSigAboveCharm_0",
    "fj_trackSipdSig_0",
    "fj_trackSipdSig_0_0",
    "fj_trackSipdSig_0_1",
    "fj_trackSipdSig_1",
    "fj_trackSipdSig_1_0",
    "fj_trackSipdSig_1_1",
    "fj_trackSipdSig_2",
    "fj_trackSipdSig_3",
    "fj_z_ratio",
]

params_1 = [
    "pfcand_ptrel",
    "pfcand_erel",
    "pfcand_phirel",
    "pfcand_etarel",
    "pfcand_deltaR",
    "pfcand_puppiw",
    "pfcand_drminsv",
    "pfcand_drsubjet1",
    "pfcand_drsubjet2",
    "pfcand_hcalFrac",
]

params_2 = [
    "track_ptrel",
    "track_erel",
    "track_phirel",
    "track_etarel",
    "track_deltaR",
    "track_drminsv",
    "track_drsubjet1",
    "track_drsubjet2",
    "track_dz",
    "track_dzsig",
    "track_dxy",
    "track_dxysig",
    "track_normchi2",
    "track_quality",
    "track_dptdpt",
    "track_detadeta",
    "track_dphidphi",
    "track_dxydxy",
    "track_dzdz",
    "track_dxydz",
    "track_dphidxy",
    "track_dlambdadz",
    "trackBTag_EtaRel",
    "trackBTag_PtRatio",
    "trackBTag_PParRatio",
    "trackBTag_Sip2dVal",
    "trackBTag_Sip2dSig",
    "trackBTag_Sip3dVal",
    "trackBTag_Sip3dSig",
    "trackBTag_JetDistVal",
]

params_3 = [
    "sv_ptrel",
    "sv_erel",
    "sv_phirel",
    "sv_etarel",
    "sv_deltaR",
    "sv_pt",
    "sv_mass",
    "sv_ntracks",
    "sv_normchi2",
    "sv_dxy",
    "sv_dxysig",
    "sv_d3d",
    "sv_d3dsig",
    "sv_costhetasvpv",
]


def main(args, save_path="", evaluating_test=True):  # noqa: C901
    print("set onnx!!!!!",args.De,args.Do,args.vv_branch, args.set_onnx )
    
    test_1_arrays = []
    test_2_arrays = []
    test_3_arrays = []
    test_spec_arrays = []
    target_test_arrays = []

    if evaluating_test:

        for test_file in sorted(glob.glob(save_path + "test_0_features_1.npy")):
            test_1_arrays.append(np.load(test_file))
        test_1 = np.concatenate(test_1_arrays)

        for test_file in sorted(glob.glob(save_path + "test_0_features_2.npy")):
            test_2_arrays.append(np.load(test_file))
        test_2 = np.concatenate(test_2_arrays)

        for test_file in sorted(glob.glob(save_path + "test_0_features_3.npy")):
            test_3_arrays.append(np.load(test_file))
        test_3 = np.concatenate(test_3_arrays)

        for test_file in sorted(glob.glob(save_path + "test_0_spectators_0.npy")):
            test_spec_arrays.append(np.load(test_file))
        test_spec = np.concatenate(test_spec_arrays)

        for test_file in sorted(glob.glob(save_path + "test_0_truth_0.npy")):
            target_test_arrays.append(np.load(test_file))
        target_test = np.concatenate(target_test_arrays)

    else:
        for test_file in sorted(glob.glob(save_path + "train_val_*_features_1.npy")):
            test_1_arrays.append(np.load(test_file))
        test_1 = np.concatenate(test_1_arrays)

        for test_file in sorted(glob.glob(save_path + "train_val_*_features_2.npy")):
            test_2_arrays.append(np.load(test_file))
        test_2 = np.concatenate(test_2_arrays)

        for test_file in sorted(glob.glob(save_path + "train_val_*_features_3.npy")):
            test_3_arrays.append(np.load(test_file))
        test_3 = np.concatenate(test_3_arrays)

        for test_file in sorted(glob.glob(save_path + "train_val_*_spectators_0.npy")):
            test_spec_arrays.append(np.load(test_file))
        test_spec = np.concatenate(test_spec_arrays)

        for test_file in sorted(glob.glob(save_path + "train_val_*_truth_0.npy")):
            target_test_arrays.append(np.load(test_file))
        target_test = np.concatenate(target_test_arrays)

    del test_1_arrays
    del test_2_arrays
    del test_3_arrays
    del test_spec_arrays
    del target_test_arrays
    test_1 = np.swapaxes(test_1, 1, 2)
    test_2 = np.swapaxes(test_2, 1, 2)
    test_3 = np.swapaxes(test_3, 1, 2)
    test_spec = np.swapaxes(test_spec, 1, 2)
    print(test_2.shape)
    print(test_3.shape)
    print(target_test.shape)
    print(test_spec.shape)
    print(target_test.shape)
    fj_pt = test_spec[:, 0, 0]
    fj_eta = test_spec[:, 1, 0]
    fj_sdmass = test_spec[:, 2, 0]
    # no_undef = np.sum(target_test,axis=1) == 1
    no_undef = fj_pt > -999  # no cut

    min_pt = -999  # 300
    max_pt = 99999  # 2000
    min_eta = -999  # no cut
    max_eta = 999  # no cut
    min_msd = -999  # 40
    max_msd = 9999  # 200

    test_1 = test_1[
        (fj_sdmass > min_msd)
        & (fj_sdmass < max_msd)
        & (fj_eta > min_eta)
        & (fj_eta < max_eta)
        & (fj_pt > min_pt)
        & (fj_pt < max_pt)
        & no_undef
    ]
    test_2 = test_2[
        (fj_sdmass > min_msd)
        & (fj_sdmass < max_msd)
        & (fj_eta > min_eta)
        & (fj_eta < max_eta)
        & (fj_pt > min_pt)
        & (fj_pt < max_pt)
        & no_undef
    ]
    test_3 = test_3[
        (fj_sdmass > min_msd)
        & (fj_sdmass < max_msd)
        & (fj_eta > min_eta)
        & (fj_eta < max_eta)
        & (fj_pt > min_pt)
        & (fj_pt < max_pt)
        & no_undef
    ]
    test_spec = test_spec[
        (fj_sdmass > min_msd)
        & (fj_sdmass < max_msd)
        & (fj_eta > min_eta)
        & (fj_eta < max_eta)
        & (fj_pt > min_pt)
        & (fj_pt < max_pt)
        & no_undef
    ]
    target_test = target_test[
        (fj_sdmass > min_msd)
        & (fj_sdmass < max_msd)
        & (fj_eta > min_eta)
        & (fj_eta < max_eta)
        & (fj_pt > min_pt)
        & (fj_pt < max_pt)
        & no_undef
    ]

    # Convert two sets into two branch with one set in both and one set in only one (Use for this file)
    test = test_2
    test_sv = test_3
    params = params_2
    params_sv = params_3

    vv_branch = args.vv_branch
    set_onnx = args.set_onnx 

    prediction = np.array([])
    batch_size = 1000#1024
    torch.cuda.empty_cache()

    from models import GraphNet

    gnn = GraphNet(
        N,
        n_targets,
        len(params),
        args.hidden,
        N_sv,
        len(params_sv),
        vv_branch=int(vv_branch),
        De=args.De,
        Do=args.Do,
    )
    print(set_onnx)
    if set_onnx==False:
        print("11")
        gnn.load_state_dict(torch.load("../../models/trained_models/gnn_new_best.pth"))
        print(sum(p.numel() for p in gnn.parameters() if p.requires_grad))
#         softmax = torchs.nn.Softmax(dim=1)

        for j in tqdm.tqdm(range(0, target_test.shape[0], batch_size)):
            dummy_input_1 = torch.from_numpy(test[j : j + batch_size]).cuda()
            dummy_input_2 = torch.from_numpy(test_sv[j : j + batch_size]).cuda()
            out_test = gnn(dummy_input_1,dummy_input_2)
#             print(np.shape(torch.from_numpy(test[j : j + batch_size])))
#             out_test = softmax(gnn(torch.from_numpy(test[j : j + batch_size]).cuda()))
            out_test = out_test.cpu().data.numpy()
#             print(np.shape(out_test))
            out_test = softmax(out_test, axis=1)
            if j == 0:
                prediction = out_test
            else:
                prediction = np.concatenate((prediction, out_test), axis=0)
            del out_test
            
#         label_ = []
#         prediction_ = []
#         for i in range(len(target_test)):
#             if [0, 0, ] == target_test[i].tolist():
#                 continue
#             else:
#                 label_.append(target_test[i].tolist())
#                 prediction_.append(prediction[i])
#         prediction = np.array(prediction_)
#         target_test = np.array(label_)
    
    else:
        print("22")
        model_path = "../../models/trained_models/onnx_model/gnn_%s.onnx" % batch_size
        onnx_soft_res = []
        for i in tqdm.tqdm(range(0, target_test.shape[0], batch_size)):
            dummy_input_1 = test[i : i + batch_size]
            dummy_input_2 = test_sv[i : i + batch_size]

            # Load the ONNX model
            model = onnx.load(model_path)

            # Check that the IR is well formed
            onnx.checker.check_model(model)

            # Print a human readable representation of the graph
            # print(onnx.helper.printable_graph(model.graph))

            options = ort.SessionOptions()
            options.intra_op_num_threads = 1
            ort_session = ort.InferenceSession(model_path, options, providers=[("CUDAExecutionProvider")])

            # compute ONNX Runtime output prediction
            ort_inputs = {ort_session.get_inputs()[0].name: dummy_input_1, ort_session.get_inputs()[1].name: dummy_input_2}
            ort_outs = ort_session.run(None, ort_inputs)

            temp_onnx_res = ort_outs[0]
#             softmax = torch.nn.Softmax(dim=1)
            
            for x in temp_onnx_res:
                x_ = softmax(x, axis=0)
                onnx_soft_res.append(x_.tolist())
          
        prediction = np.array(onnx_soft_res)
#         prediction = []
#         label_ = []
#         for i in range(len(target_test)):
#             if [0, 0, ] == target_test[i].tolist():
#                 continue
#             else:
#                 label_.append(target_test[i].tolist())
#                 prediction.append(onnx_soft_res[i])
#         prediction = np.array(prediction)
#         target_test = np.array(label_)

    print(target_test.shape, prediction.shape)
    auc = roc_auc_score(target_test[:, 1], prediction[:, 1])
    print("AUC: ", auc)
    acc = accuracy_score(target_test[:, 0], prediction[:, 0] >= 0.5)
    print("Accuray: ", acc)
    # checking the sums
    target_sums = np.sum(target_test, 1)
    prediction_sums = np.sum(prediction, 1)
    idx = target_sums == 1
    print("Total: {}, Target: {}, Pred: {}".format(np.sum(idx), np.sum(target_sums[idx]), np.sum(prediction_sums[idx])))
    auc = roc_auc_score(target_test[idx][:, 1], prediction[idx][:, 1])
    print("AUC: ", auc)
    acc = accuracy_score(target_test[idx][:, 0], prediction[idx][:, 0] >= 0.5)
    print("Accuray 0: ", acc)
    acc = accuracy_score(target_test[idx][:, 1], prediction[idx][:, 1] >= 0.5)
    print("Accuray 1: ", acc)
    idx_bar = target_sums != 1
    print(target_test[idx_bar][0:10, :])


if __name__ == "__main__":
    """This is executed when run from the command line"""
    parser = argparse.ArgumentParser()

    # Required positional arguments
    parser.add_argument("outdir", help="Required output directory")
    parser.add_argument("vv_branch", help="Required positional argument")
    # Optional arguments
    parser.add_argument("--De", type=int, action="store", dest="De", default=5, help="De")
    parser.add_argument("--Do", type=int, action="store", dest="Do", default=6, help="Do")
    parser.add_argument("--hidden", type=int, action="store", dest="hidden", default=15, help="hidden")
    parser.add_argument("--set_onnx", action="store_true", dest="set_onnx",default=False, help="set_onnx")
    
    
    args = parser.parse_args()
    main(args, save_path_test, True)
