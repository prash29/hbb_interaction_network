from datetime import datetime
import argparse
import glob
import os
from pathlib import Path

import numpy as np
import torch

# if torch.cuda.is_available():
#     import setGPU  # noqa: F401

import tqdm
import yaml
from scipy.special import softmax
from sklearn.metrics import accuracy_score, roc_auc_score, roc_curve

from src.data.h5data import H5Data
from src.models.InteractionNet import InteractionNetSingleTagger, InteractionNetTagger
from src.models.pretrain_vicreg import Projector, VICReg, get_backbones

project_dir = Path(__file__).resolve().parents[2]
definitions = f"{project_dir}/src/data/definitions.yml"
with open(definitions) as yaml_file:
    defn = yaml.load(yaml_file, Loader=yaml.FullLoader)

N = defn["nobj_2"]  # number of charged particles
N_sv = defn["nobj_3"]  # number of SVs
n_targets = len(defn["reduced_labels"])  # number of classes
spectators = defn["spectators"]
params = defn["features_2"]
params_sv = defn["features_3"]


def main(args, evaluating_test=True):  # noqa: C901

    device = args.device
    batch_size = args.batch_size

    files_test = glob.glob(os.path.join(args.save_path, "newdata_*.h5"))

    if evaluating_test:
        dataset = "test"
    else:
        dataset = "train"

    data_test = H5Data(
        batch_size=batch_size,
        cache=None,
        preloading=0,
        features_name=f"{dataset}ing_subgroup",
        labels_name="target_subgroup",
        spectators_name="spectator_subgroup",
    )
    data_test.set_file_names(files_test)
    n_test = data_test.count_data()
    print(f"test data: {n_test}")

    min_pt = args.min_pt
    max_pt = args.max_pt
    min_eta = args.min_eta
    max_eta = args.max_eta
    min_msd = args.min_msd
    max_msd = args.max_msd

    if args.load_vicreg_path:
        args.x_inputs = len(params)
        args.y_inputs = len(params_sv)
        args.x_backbone, args.y_backbone = get_backbones(args)
        args.return_embedding = False
        args.return_representation = True
        vicreg = VICReg(args).to(args.device)
        vicreg.load_state_dict(torch.load(args.load_vicreg_path))
        vicreg.eval()
        model = Projector(args.finetune_mlp, 2 * vicreg.x_backbone.Do).to(device)
    else:
        if args.just_svs:
            model = InteractionNetSingleTagger(
                dims=N_sv,
                num_classes=n_targets,
                features_dims=len(params_sv),
                hidden=args.hidden,
                De=args.De,
                Do=args.Do,
            ).to(device)
        elif args.just_tracks:
            model = InteractionNetSingleTagger(
                dims=N,
                num_classes=n_targets,
                features_dims=len(params),
                hidden=args.hidden,
                De=args.De,
                Do=args.Do,
            ).to(device)
        else:
            model = InteractionNetTagger(
                pf_dims=N,
                sv_dims=N_sv,
                num_classes=n_targets,
                pf_features_dims=len(params),
                sv_features_dims=len(params_sv),
                hidden=args.hidden,
                De=args.De,
                Do=args.Do,
            ).to(device)
    model.load_state_dict(torch.load(args.load_path))
    model.eval()
    print(f"Parameters = {sum(p.numel() for p in model.parameters() if p.requires_grad)}")

    # test process
    iterator = data_test.generate_data()
    total_ = int(n_test / batch_size)
    pbar = tqdm.tqdm(iterator, total=total_)
    for j, element in enumerate(pbar):
        (sub_X, sub_Y, sub_Z) = element
        training = sub_X[2]
        training_sv = sub_X[3]
        target = sub_Y[0]
        spectator = sub_Z[0]

        # mask away selection
        fj_pt = spectator[:, 0, 0]
        fj_eta = spectator[:, 0, 1]
        fj_sdmass = spectator[:, 0, 2]
        if args.no_undef:
            no_undef = np.sum(target, axis=1) == 1
        else:
            no_undef = fj_pt > -999  # no cut
        mask = (
            (fj_sdmass > min_msd)
            & (fj_sdmass < max_msd)
            & (fj_eta > min_eta)
            & (fj_eta < max_eta)
            & (fj_pt > min_pt)
            & (fj_pt < max_pt)
            & no_undef
        )
        training = training[mask]
        training_sv = training_sv[mask]
        target = target[mask]
        spectator = spectator[mask]

        trainingv = torch.tensor(training, dtype=torch.float, device=device)
        trainingv_sv = torch.tensor(training_sv, dtype=torch.float, device=device)

        if args.load_vicreg_path:
            representation, representation_sv = vicreg(trainingv, trainingv_sv)
            out_test = model(torch.cat((representation, representation_sv), dim=-1))
        else:
            if args.just_svs:
                out_test = model(trainingv_sv)
            elif args.just_tracks:
                out_test = model(trainingv)
            else:
                out_test = model(trainingv, trainingv_sv)
        out_test = out_test.cpu().data.numpy()
        out_test = softmax(out_test, axis=1)
        if j == 0:
            prediction = out_test
            target_test = target
        else:
            prediction = np.concatenate((prediction, out_test), axis=0)
            target_test = np.concatenate((target_test, target))

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

    eval_path = args.eval_path

    # pu_label for npv
    low_pu = "max_npv_15" in args.save_path
    high_pu = "min_npv_15" in args.save_path

    if low_pu:
        pu_label = "max_npv_15"
    elif high_pu:
        pu_label = "min_npv_15"
    else:
        pu_label = eval_path

    fpr, tpr, _ = roc_curve(target_test[:, 1], prediction[:, 1])

    # Make sure to have created a subdirectory for model performance in the job yaml, like 
    # cd models/model_performances && mkdir max_pt
    # where max_pt is the eval_path

    # save to subdirectory created above
    model_perf_loc = f"{args.outdir}/model_performances/" + eval_path  
    os.makedirs(model_perf_loc, exist_ok=True)
    model_name = Path(args.load_path).stem

    np.save(
        f"{model_perf_loc}/{model_name}_test_fpr_{pu_label}.npy",
        fpr,
    )
    np.save(
        f"{model_perf_loc}/{model_name}_test_tpr_{pu_label}.npy",
        tpr,
    )


if __name__ == "__main__":
    """This is executed when run from the command line"""
    parser = argparse.ArgumentParser()

    # Optional arguments
    parser.add_argument(
        "--save-path",
        type=str,
        action="store",
        default=f"{project_dir}/data/processed/test/",
        help="Input directory with testing files",
    )
    parser.add_argument(
        "--eval-path",
        type=str,
        action="store",
        default=str(datetime.now()),
        help="the evaluation results will be saved at model_performances/eval-path",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        action="store",
        dest="outdir",
        default=f"{project_dir}/models/",
        help="Output directory",
    )
    parser.add_argument(
        "--min-msd",
        type=float,
        action="store",
        default=40.0,
        help="Min mSD for evaluation",
    )
    parser.add_argument(
        "--max-msd",
        type=float,
        action="store",
        default=200.0,
        help="Max mSD for evaluation",
    )
    parser.add_argument(
        "--min-pt",
        type=float,
        action="store",
        default=300.0,
        help="Min pT for evaluation",
    )
    parser.add_argument(
        "--max-pt",
        type=float,
        action="store",
        default=2000.0,
        help="Max pT for evaluation",
    )
    parser.add_argument(
        "--min-eta",
        type=float,
        action="store",
        default=-999.0,
        help="Min eta for evaluation",
    )
    parser.add_argument(
        "--max-eta",
        type=float,
        action="store",
        default=999.0,
        help="Max eta for evaluation",
    )
    parser.add_argument("--De", type=int, action="store", dest="De", default=32, help="De")
    parser.add_argument("--Do", type=int, action="store", dest="Do", default=64, help="Do")
    parser.add_argument("--hidden", type=int, action="store", dest="hidden", default=128, help="hidden")
    parser.add_argument(
        "--batch-size",
        type=int,
        action="store",
        dest="batch_size",
        default=1024,
        help="batch_size",
    )
    parser.add_argument(
        "--device",
        action="store",
        dest="device",
        default="cpu",
        help="device to evaluate model; follow pytorch convention",
    )
    parser.add_argument(
        "--no-undef",
        action="store_true",
        help="no undefined labels for evaluation",
    )
    parser.add_argument(
        "--load-path",
        type=str,
        action="store",
        default=f"{project_dir}/models/trained_models/gnn_new_best.pth",
        help="Load weights from model if enabled",
    )
    parser.add_argument(
        "--load-vicreg-path",
        type=str,
        action="store",
        default=None,
        help="Load weights from vicreg model if enabled",
    )
    parser.add_argument(
        "--just-svs",
        action="store_true",
        default=False,
        help="Consider just secondary vertices in model",
    )
    parser.add_argument(
        "--just-tracks",
        action="store_true",
        default=False,
        help="Consider just tracks in model",
    )
    parser.add_argument(
        "--shared",
        action="store_true",
        help="share parameters of backbone",
    )
    parser.add_argument(
        "--transform-inputs",
        type=int,
        action="store",
        dest="transform_inputs",
        default=32,
        help="transform_inputs",
    )
    parser.add_argument(
        "--mlp",
        default="256-256-256",
        help="Size and number of layers of the MLP expander head",
    )
    parser.add_argument(
        "--finetune-mlp",
        default="2",
        help="Size and number of layers of the MLP finetuning head",
    )

    args = parser.parse_args()
    main(args, True)
