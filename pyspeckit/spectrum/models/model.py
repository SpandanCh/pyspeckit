import numpy as np
from mpfit import mpfit
import copy
import matplotlib.cbook as mpcb

class SpectralModel(object):

    def __init__(self, modelfunc, npars, parnames=None, parvalues=None,
            parlimits=None, parlimited=None, parfixed=None, parerror=None,
            partied=None, fitunits=None, parsteps=None, npeaks=1,
            shortvarnames=("A","v","\\sigma"), **kwargs):

        self.modelfunc = modelfunc
        self.npars = npars
        self.parnames = parnames
        self.fitunits = fitunits
        self.npeaks = npeaks
        self.shortvarnames = shortvarnames

        temp_pardict = dict([(varname, np.zeros(self.npars, dtype='bool')) if locals()[varname] is None else (varname, locals()[varname])
            for varname in str.split("parnames,parvalues,parsteps,parlimits,parlimited,parfixed,parerror,partied",",")])

        # generate the parinfo dict
        # note that 'tied' must be a blank string (i.e. ""), not False, if it is not set
        # parlimited, parfixed, and parlimits are all two-element items (tuples or lists)
        self.parinfo = [ {'n':ii,
            'value':temp_pardict['parvalues'][ii],
            'step':temp_pardict['parsteps'][ii],
            'limits':temp_pardict['parlimits'][ii],
            'limited':temp_pardict['parlimited'][ii],
            'fixed':temp_pardict['parfixed'][ii],
            'parname':temp_pardict['parnames'][ii],
            'error':temp_pardict['parerror'][ii],
            'tied':temp_pardict['partied'][ii] if temp_pardict['partied'][ii] else ""} 
            for ii in xrange(self.npars)]

        self.modelfunc_kwargs = kwargs

    def mpfitfun(self,x,y,err):
        if err is None:
            def f(p,fjac=None): return [0,(y-self.modelfunc(x,*p, **self.modelfunc_kwargs))]
        else:
            def f(p,fjac=None): return [0,(y-self.modelfunc(x,*p, **self.modelfunc_kwargs))/err]
        return f

    def __call__(self, xax, data, err=None, params=[], quiet=True, shh=True,
            veryverbose=False, npeaks=None, **kwargs):
        """
        Run the fitter
        """

        if npeaks is not None:
            self.npeaks = npeaks

        if len(params) == self.npars:
            for par,guess in zip(self.parinfo,params):
                par['value'] = guess
        
        for varname in str.split("limits,limited,fixed,tied",","):
            if varname in kwargs:
                var = kwargs.pop(varname)
                for pi in self.parinfo:
                    pi[varname] = var[pi['n']]

        if hasattr(xax,'convert_to_unit') and self.fitunits is not None:
            # some models will depend on the input units.  For these, pass in an X-axis in those units
            # (gaussian, voigt, lorentz profiles should not depend on units.  Ammonia, formaldehyde,
            # H-alpha, etc. should)
            xax = copy.copy(xax)
            xax.convert_to_unit(self.fitunits, quiet=quiet)

        if err is None:
            err = np.ones(data.shape)
        if np.any(np.isnan(data)) or np.any(np.isinf(data)):
            err[np.isnan(data) + np.isinf(data)] = np.inf
            data[np.isnan(data) + np.isinf(data)] = 0

        mp = mpfit(self.mpfitfun(xax,data,err),parinfo=self.parinfo,quiet=quiet,**kwargs)
        mpp = mp.params
        if mp.perror is not None: mpperr = mp.perror
        else: mpperr = mpp*0
        chi2 = mp.fnorm

        if mp.status == 0:
            raise Exception(mp.errmsg)

        if (not shh) or veryverbose:
            print "Fit status: ",mp.status
            print "Fit error message: ",mp.errmsg
            print "Fit message: ",mpfit_messages[mp.status]
            for i,p in enumerate(mpp):
                self.parinfo[i]['value'] = p
                print self.parinfo[i]['parname'],p," +/- ",mpperr[i]
            print "Chi2: ",mp.fnorm," Reduced Chi2: ",mp.fnorm/len(data)," DOF:",len(data)-len(mpp)

        self.mp = mp
        self.mpp = mpp#[1:]
        self.mpperr = mpperr#[1:]
        self.model = self.modelfunc(xax,*mpp,**self.modelfunc_kwargs)
        return mpp,self.model,mpperr,chi2


    def annotations(self, shortvarnames=None):
        svn = self.shortvarnames if shortvarnames is None else shortvarnames
        label_list = [(
                "$%s(%i)$=%6.4g $\\pm$ %6.4g" % (svn[ii],jj,self.mpp[ii+jj*self.npars],self.mpperr[ii+jj*self.npars]),
                          ) for ii in range(len(svn)) for jj in range(self.npeaks)]
        labels = tuple(mpcb.flatten(label_list))
        return labels

