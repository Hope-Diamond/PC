import torch
from tqdm import tqdm
from nets.pspnet_training import CE_Loss, Dice_loss, Focal_Loss
from utils.utils import get_lr
from utils.utils_metrics import f_score

def fit_one_epoch(model_train, model, loss_history, optimizer, epoch, epoch_step, epoch_step_val, gen, gen_val, Epoch, cuda, dice_loss, focal_loss, cls_weights, aux_branch, num_classes):
    total_loss      = 0
    total_f_score   = 0

    val_loss        = 0
    val_f_score     = 0

    model_train.train()
    print('Start Train')
    with tqdm(total=epoch_step,desc=f'Epoch {epoch + 1}/{Epoch}',postfix=dict,mininterval=0.3) as pbar:
        for iteration, batch in enumerate(gen):
            if iteration >= epoch_step: 
                break
            imgs, pngs, labels = batch

            with torch.no_grad():
                imgs    = torch.from_numpy(imgs).type(torch.FloatTensor)
                pngs    = torch.from_numpy(pngs).long()
                labels  = torch.from_numpy(labels).type(torch.FloatTensor)
                weights = torch.from_numpy(cls_weights)
                if cuda:
                    imgs    = imgs.cuda()
                    pngs    = pngs.cuda()
                    labels  = labels.cuda()
                    weights = weights.cuda()

            optimizer.zero_grad()
            if aux_branch:
                aux_outputs, outputs = model_train(imgs)
                if focal_loss:
                    aux_loss  = Focal_Loss(outputs, pngs, weights, num_classes = num_classes)
                    main_loss = Focal_Loss(outputs, pngs, weights, num_classes = num_classes)
                else:
                    aux_loss  = CE_Loss(aux_outputs, pngs, weights, num_classes = num_classes)
                    main_loss = CE_Loss(outputs, pngs, weights, num_classes = num_classes)
                loss      = aux_loss + main_loss
                if dice_loss:
                    aux_dice  = Dice_loss(aux_outputs, labels)
                    main_dice = Dice_loss(outputs, labels)
                    loss      = loss + aux_dice + main_dice
            else:
                outputs = model_train(imgs)
                if focal_loss:
                    loss = Focal_Loss(outputs, pngs, weights, num_classes = num_classes)
                else:
                    loss = CE_Loss(outputs, pngs, weights, num_classes = num_classes)

                if dice_loss:
                    main_dice = Dice_loss(outputs, labels)
                    loss      = loss + main_dice

            with torch.no_grad():
                #-------------------------------#
                #   计算f_score
                #-------------------------------#
                _f_score = f_score(outputs, labels)

            loss.backward()
            optimizer.step()

            total_loss      += loss.item()
            total_f_score   += _f_score.item()
            
            pbar.set_postfix(**{'total_loss': total_loss / (iteration + 1), 
                                'f_score'   : total_f_score / (iteration + 1),
                                'lr'        : get_lr(optimizer)})
            pbar.update(1)

    print('Finish Train')

    model_train.eval()
    print('Start Validation')
    with tqdm(total=epoch_step_val, desc=f'Epoch {epoch + 1}/{Epoch}',postfix=dict,mininterval=0.3) as pbar:
        for iteration, batch in enumerate(gen_val):
            if iteration >= epoch_step_val:
                break
            imgs, pngs, labels = batch
            with torch.no_grad():
                imgs    = torch.from_numpy(imgs).type(torch.FloatTensor)
                pngs    = torch.from_numpy(pngs).long()
                labels  = torch.from_numpy(labels).type(torch.FloatTensor)
                weights = torch.from_numpy(cls_weights)
                if cuda:
                    imgs    = imgs.cuda()
                    pngs    = pngs.cuda()
                    labels  = labels.cuda()
                    weights = weights.cuda()
                #-------------------------------#
                #   判断是否使用辅助分支
                #-------------------------------#
                if aux_branch:
                    aux_outputs, outputs = model_train(imgs)
                    if focal_loss:
                        aux_loss  = Focal_Loss(outputs, pngs, weights, num_classes = num_classes)
                        main_loss = Focal_Loss(outputs, pngs, weights, num_classes = num_classes)
                    else:
                        aux_loss  = CE_Loss(aux_outputs, pngs, weights, num_classes = num_classes)
                        main_loss = CE_Loss(outputs, pngs, weights, num_classes = num_classes)
                    loss      = aux_loss + main_loss
                    if dice_loss:
                        aux_dice  = Dice_loss(aux_outputs, labels)
                        main_dice = Dice_loss(outputs, labels)
                        loss      = loss + aux_dice + main_dice
                else:
                    outputs = model_train(imgs)
                    if focal_loss:
                        loss = Focal_Loss(outputs, pngs, weights, num_classes = num_classes)
                    else:
                        loss = CE_Loss(outputs, pngs, weights, num_classes = num_classes)

                    if dice_loss:
                        main_dice = Dice_loss(outputs, labels)
                        loss      = loss + main_dice
                #-------------------------------#
                #   计算f_score
                #-------------------------------#
                _f_score    = f_score(outputs, labels)

                val_loss    += loss.item()
                val_f_score += _f_score.item()
                
            
            pbar.set_postfix(**{'total_loss': val_loss / (iteration + 1),
                                'f_score'   : val_f_score / (iteration + 1),
                                'lr'        : get_lr(optimizer)})
            pbar.update(1)
            
    loss_history.append_loss(total_loss / epoch_step, val_loss / epoch_step_val)
    print('Finish Validation')
    print('Epoch:'+ str(epoch+1) + '/' + str(Epoch))
    print('Total Loss: %.3f || Val Loss: %.3f ' % (total_loss / epoch_step, val_loss / epoch_step_val))
    torch.save(model.state_dict(), 'logs/ep%03d-loss%.3f-val_loss%.3f.pth'%((epoch + 1), total_loss / epoch_step, val_loss / epoch_step_val))
