# HandwritenFormularToLatex
Converting handwritten formulas to LaTeX

- References:
    + [Handwritten equations to LaTeX](http://opensourc.es/blog/he2latex)
    
    + [On Machine Understanding of Online Handwritten Mathematical Expressions](https://github.com/chimtrangbu/HandwritenFormularToLatex/blob/master/References/Online_handwritten_equations.pdf)
    
    + [Image-to-Markup Generation with Coarse-to-Fine Attention](http://lstm.seas.harvard.edu/latex/)


- Download dataset of [85 diffirent math symbols in handwriting](https://www.kaggle.com/xainano/handwrittenmathsymbols) from Kaggle 
    -> folder 'extracted_images'


- Create dataset of mathematical formulas by [Generator](https://github.com/chimtrangbu/HandwritenFormularToLatex/blob/master/generate.ipynb)
    
    + Extracting 23 symbols ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '-', '+', '=', 'leq', 'neq', 'geq', 'alpha', 'beta', 'lambda', 'lt', 'gt', 'x', 'y'] from Kaggle's dataste
    
    + Normalization of symbols -> folder **normalized**
    
        • Removing the border
        
        • Scale to at most 40 × 40
        
        • Center the mass in a 48 × 48 image
        
        • Subtract mean and divide by standard deviation
    
    + Combining symbols to easy formula -> folder **formulas**
    
- [Generate sequences](https://github.com/chimtrangbu/HandwritenFormularToLatex/blob/master/generate_sequences.ipynb)
    + Available files: [source](https://github.com/Wikunia/HE2LaTeX) 
        
        • train_images_std.npy
        
        • train_images_mean.npy
        
        • Latex/Latex.py
        
        • Seq2SeqModel/Seq2SeqModel.py
        
        • seq_mod/
    
    + Generate latex sequences from filenames using [Sequence-to-sequence model](https://github.com/chimtrangbu/HandwritenFormularToLatex/tree/master/Seq2SeqModel)
        -> output files: **oseq_n.npy, iseq_n.npy, files.json**
        
-> output files: [drive](https://drive.google.com/drive/folders/1qrbi1yu0b6IVh9sWkY3dTTPHWbuFEi57?usp=sharing)

- Train and test the seq2seq model: https://github.com/Wikunia/HE2LaTeX/blob/master/Seq2Seq.ipynb
    train in ~ 5 hours -> Accuracy on test set ~ 62%

- To be continue
