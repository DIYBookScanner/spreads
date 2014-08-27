/** @jsx React.DOM */
/* global module, require, console */

/*
 * Copyright (C) 2014 Johannes Baiter <johannes.baiter@gmail.com>
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.

 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

(function() {
  'use strict';

  var React = require('react/addons'),
      _ = require('underscore'),
      Mousetrap = require('mousetrap'),
      F = require('./foundation.js'),
      ModelMixin = require('../../vendor/backbonemixin.js'),
      LoadingOverlay = require('./overlays.js').Activity,
      lightbox = require('./overlays.js').LightBox,
      LayeredComponentMixin = require('./overlays.js').LayeredComponentMixin,
      PluginWidget = require('./config.js').PluginWidget,
      CropWidget = require('./cropdialog.js'),
      util = require('../util.js');

  var placeholderImg = "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAKAAAAB4AQMAAABPbGssAAAAA1BMVEWZmZl86KQWAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3gQIFjciiRhnwgAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAAAZSURBVEjH7cEBDQAAAMKg909tDwcUAAAPBgnYAAHW6F1SAAAAAElFTkSuQmCC";


  var StatusDisplay = React.createClass({
    propTypes: {
      numPages: React.PropTypes.number.isRequired,
      numExpected: React.PropTypes.number,
      captureStart: React.PropTypes.number
    },

    getInitialState: function() {
      return {
        initialNum: this.props.numPages
      }
    },

    render: function() {
      // This is only >0 when the 'extent' metadata field is a number, this
      // allows us to display a progress bar that allows for some visual
      // feedback on how far a long the user is with a capture.
      var progress = Math.min(1, this.props.numPages/this.props.numExpected);
      var speed;
      if (this.props.captureStart) {
        var elapsed = (new Date().getTime()/1000) - this.props.captureStart;
        var shot = this.props.numPages - this.state.initialNum;
        speed = (3600/elapsed)*shot | 0;
      } else {
        speed = 0.0;
      }

      return (
        <div>
          {this.props.numExpected > 0 &&
          <F.Row>
            <F.Column>
              <div className="nice secondary progress">
                <span className="meter" style={{width: progress*100+'%'}} />
              </div>
            </F.Column>
          </F.Row>}
          <F.Row className="capture-info">
            <F.Column size={6}>
              <span className="pagecount">{this.props.numPages} pages</span>
            </F.Column>
            {speed > 0 &&
            <F.Column size={6}>
              <span className="capturespeed">{speed} pages/hour</span>
            </F.Column>}
          </F.Row>
        </div>
      );
    }
  });


  var Preview = React.createClass({
    mixins: [LayeredComponentMixin],

    propTypes: {
      targetPage: React.PropTypes.oneOf(["odd", "even"]).isRequired,
      imageSrc: React.PropTypes.string,
      cropParams: React.PropTypes.object,
      onCropParamUpdate: React.PropTypes.func,
      showCropPreview: React.PropTypes.bool
    },

    getInitialState: function() {
      return {
        displayLightbox: false,
        displayCrop: false,
      };
    },

    toggleCropDisplay: function() {
      this.setState({
        displayCrop: !this.state.displayCrop
      });
    },

    getCropPreviewStyle: function() {
      if (!this.isMounted() || _.isEmpty(this.props.cropParams)) return {};
      var domNode = this.refs.previewImage.getDOMNode();
      var cropParams = this.props.cropParams,
          factor = domNode.offsetWidth / cropParams.nativeWidth,
          thumbOffset = domNode.offsetLeft;
      return {
        left: thumbOffset + Math.ceil(cropParams.left*factor),
        top: Math.ceil(cropParams.top*factor),
        width: Math.ceil(cropParams.width*factor),
        height: Math.ceil(cropParams.height*factor)
      };
    },

    toggleLightbox: function() {
      this.setState({
        displayLightbox: !this.state.displayLightbox
      });
    },

    handleSave: function(params) {
      this.toggleCropDisplay();
      this.props.onCropParamUpdate(params);
    },

    render: function() {
      var cropPreviewStyle = this.props.showCropPreview ? this.getCropPreviewStyle() : {};
      var imageSrc = this.props.imageSrc + "?numtype=capture";
      var thumbSrc = this.props.imageSrc + "/thumb?numtype=capture"
      return (
        <li>
          {this.props.imageSrc &&
          <a className="toggle-crop" title="Crop image" onClick={this.toggleCropDisplay}>
            <i className="fa fa-crop" /> Crop
          </a>}
          {this.props.imageSrc ?
            <a title="Open full resolution image in lightbox"
               onClick={this.toggleLightbox}>
              <img className={this.props.targetPage}
                   src={thumbSrc} ref='previewImage'/>
            </a>:
            <img className={"placeholder " + this.props.targetPage}
                 src={placeholderImg}/>}
          {!_.isEmpty(cropPreviewStyle) &&
           <div className="crop-preview" style={cropPreviewStyle}/>}
        </li>
      );
    },

    renderLayer: function() {
      var imageSrc = this.props.imageSrc + "?numtype=capture";
      return (
        <div>
          {this.state.displayLightbox &&
            <lightbox onClose={this.toggleLightbox} src={imageSrc} />}
          {this.state.displayCrop &&
            <F.Modal onClose={this.toggleCropDisplay} small={false}>
              <CropWidget imageSrc={imageSrc}
                          onSave={this.handleSave}
                          cropParams={this.props.cropParams} showInputs={true} />
            </F.Modal>}
        </div>);
    }
  });


  var ConfigModal = React.createClass({
    propTypes: {
      workflow: React.PropTypes.object.isRequired,
      onClose: React.PropTypes.func.isRequired,
      onConfirm: React.PropTypes.func.isRequired
    },

    getInitialState: function() {
      return {
        advancedOpts: false,
        validationErrors: {}
      };
    },

    toggleAdvanced: function() {
      this.setState({
        advancedOpts: !this.state.advancedOpts
      });
    },

    handleSubmit: function() {
      this.props.workflow.on('validated:invalid', function(workflow, errors) {
        this.setState({validationErrors: errors});
      }, this);
      var xhr = this.props.workflow.save();
      if (xhr) {
        xhr.done(function() {
          this.props.workflow.off('validated:invalid', null, this);
          this.props.onConfirm();
        }.bind(this))
      };
    },

    render: function() {
      return (
        <form onSubmit={this.handleSubmit}>
          <F.ConfirmModal onCancel={this.props.onClose}
                          onConfirm={this.handleSubmit}>
            <h2>Configure Devices</h2>
            <input id="check-advanced" type="checkbox"
                   value={this.state.advancedOpts}
                   onChange={this.toggleAdvanced} />
            <label htmlFor="check-advanced">Show advanced options</label>
            <PluginWidget template={window.pluginTemplates.device}
                          cfgValues={this.props.workflow.get('config').device}
                          errors={this.state.validationErrors}
                          showAdvanced={this.state.advancedOpts}
                          onChange={function(vals) {
                            var config = _.clone(this.props.workflow.get('config'));
                            config.device = vals;
                            this.props.workflow.set('config', config);
                          }.bind(this)} />
          </F.ConfirmModal>
        </form>
      );
    }
  });


  var Control = React.createClass({
    mixins: [LayeredComponentMixin],

    propTypes: {
      workflow: React.PropTypes.object.isRequired,
      onConfigUpdate: React.PropTypes.func.isRequired,
      onFinish: React.PropTypes.func.isRequired
    },

    getInitialState: function() {
      return {
        displayConfig: false
      };
    },

    componentWillMount: function() {
      // Bind keyboard shortcuts
      _.each(window.config.core.capture_keys, function(key) {
        if (key === ' ') key = 'space';
        Mousetrap.bind(key, this.handleCapture);
      }, this);
      Mousetrap.bind('r', this.handleRetake);
      Mousetrap.bind('f', this.props.onFinish);
    },

    componentWillUnmount: function() {
      _.each(window.config.core.capture_key, function(key) {
        if (key === ' ') key = 'space';
        Mousetrap.unbind(key);
      });
      Mousetrap.unbind('r');
      Mousetrap.unbind('f');
    },

    toggleConfigModal: function() {
      this.setState({
        displayConfig: !this.state.displayConfig
      });
    },

    /**
     * Trigger a single capture, display activity overlay until it is finished
     */
    handleCapture: function() {
      if (this.state.waiting) return;
      this.props.workflow.triggerCapture();
    },

    handleConfigUpdate: function() {
      if (this.state.waiting) return;
      this.toggleConfigModal();
      this.props.onConfigUpdate();
    },

    /**
     * Trigger a retake (= delete last <num_devices> captures and take new
     * ones, display activity overlay until it is finished.
     */
    handleRetake: function() {
      if (this.state.waiting)  return;
      this.props.workflow.triggerCapture({retake: true});
    },

    render: function() {
      return (
        <F.Row>
          <F.Column className="capture-controls">
            <ul>
              <li id="retake-capture">
                <F.Button title="Discard last capture and take a new one"
                          onClick={this.handleRetake} secondary={true}>
                  <i className="fa fa-refresh"></i>
                </F.Button>
              </li>
              <li id="trigger-capture">
                <F.Button title="Trigger capture" onClick={this.handleCapture}>
                  <i className="fa fa-camera"></i>
                </F.Button>
              </li>
              <li>
                <F.Button title="Configure devices" onClick={this.toggleConfigModal}
                          secondary={true}>
                  <i className="fa fa-gear"></i>
                </F.Button>
              </li>
              <li>
                <F.Button title="Finish capture and return to workflow list"
                          onClick={this.props.onFinish} className="complete">
                  <i className="fa fa-check"></i>
                </F.Button>
              </li>
            </ul>
          </F.Column>
        </F.Row>
      );
    },

    renderLayer: function() {
      if (this.state.displayConfig) {
        return (<ConfigModal workflow={this.props.workflow}
                             onClose={this.toggleConfigModal}
                             onConfirm={this.handleConfigUpdate} />);
      } else {
        return null;
      }
    }
  });


  var ShortcutHelp = React.createClass({
    propTypes: {
      captureKeys: React.PropTypes.arrayOf(React.PropTypes.string)
    },

    render: function() {
      if (util.isTouchDevice()) return null;
      return (
        <F.Row className="hide-for-touch">
          <F.Column size={4} offset={4} className="shortcuts">
            <strong>Keyboard shortcuts:</strong>
            <ul>
              <li>Capture:
                {_.map(this.props.captureKeys, function(key) {
                  return (<span key={key}>{' '}<kbd>{key.toUpperCase()}</kbd></span>);
                })}</li>
              <li>Retake: <kbd>R</kbd></li>
              <li>Finish: <kbd>F</kbd></li>
            </ul>
          </F.Column>
        </F.Row>
      );
    }
  });


  /**
   * Screen component to control the capture process.
   */
  var CaptureScreen = React.createClass({
    propTypes: {
      workflow: React.PropTypes.object.isRequired
    },

    /** Enables two-way databinding with Backbone model */
    mixins: [ModelMixin, LayeredComponentMixin],

    /** Activates databinding for `workflow` model property. */
    getBackboneModels: function() {
      return [this.props.workflow];
    },

    getInitialState: function() {
      // Try to load cropParams for this workflow from localStorage
      return {
        /** Display activity overlay? */
        waiting: false,
        /** Message for activity overlay */
        waitMessage: undefined,
        /** Crop parameters */
        cropParams: {},
        /** Whether we registered a function to crop on successful captures */
        cropOnSuccess: false,
        /** Time of first capture */
        captureStart: undefined
      };
    },

    componentWillMount: function() {
      // Display waiting modal during ongoing capture
      this.props.workflow.on('capture-triggered', function(){
        this.toggleWaiting("Please wait for the capture to finish...");
      }, this);
      this.props.workflow.on('capture-succeeded', this.toggleWaiting, this);

      // Record time of first capture
      this.props.workflow.on('capture-succeeded', _.once(function() {
        this.setState({
          captureStart: new Date().getTime()/1000
        });
      }), this);

      window.router.before = function(route, name) {
        this.setState({
          returnRoute: route
        });
        this.handleFinish();
        return false;
      }.bind(this)

      window.addEventListener("beforeunload", function(event) {
        this.props.workflow.finishCapture();
      }.bind(this));

      // Disable waiting screen if there was an error
      function disableWaiting() {
        if (this.state.waiting) this.setState({waiting: false})
      };
      window.router.events.on('apierror', disableWaiting, this);
      this.props.workflow.on('capture-failed', disableWaiting, this);

      // Leave capture screen when the workflow step is changed from elsewhere
      this.props.workflow.on('status-updated', function(status) {
        if (status.step !== 'capture') {
          window.router.navigate('/', {trigger: true});
        }
      }, this);
    },

    componentDidMount: function() {
      // Prepare devices
      this.toggleWaiting("Please wait while the devices  are being prepared " +
                          "for capture");
      this.props.workflow.prepareCapture({onSuccess: this.toggleWaiting});

      var storageKey = 'crop-params.' + this.props.workflow.id,
          cropParamJson = localStorage.getItem(storageKey),
          cropParams;
      if (cropParamJson) {
        // If there are crop parameters in the localStorage for this scan,
        // the pages preceding the first shot are (likely, TODO) already cropped,
        // so we only register the crop callback after the first capture has
        // already happened.
        this.props.workflow.once('capture-succeeded', this.bindCropEvents, this);
        this.setState({
          cropParams: JSON.parse(cropParamJson),
          cropTarget: undefined
        });
      }
    },

    /**
     * Triggers finish of capture on workflow.
     */
    componentWillUnmount: function() {
      console.log("Wrapping up capture process");

      // Remove event listeners
      this.props.workflow.off(null, null, this);

      // Crop last two shot images
      if (this.state.cropOnSuccess && !_.isEmpty(this.state.cropParams)) {
        _.each(this.props.workflow.get('pages').slice(-2), function(page) {
            var targetPage = page.sequence_num%2 > 0 ? 'odd': 'even';
            this.props.workflow.cropPage({
              pageNum: page.capture_num,
              cropParams: this.state.cropParams[targetPage]
            });
        }, this);
      }
    },

    handleFinish: function() {
      delete window.router.before;
      function leaveScreen() {
        window.router.navigate(this.state.returnRoute || '/',
                               {trigger: true});
      }
      this.toggleWaiting("Please wait for the capture process to finish...");
      this.props.workflow.finishCapture({onSuccess: leaveScreen.bind(this)});
    },

    /**
     * For each page number 'n' in data.pages, crop the page 'n-2' with
     * the appropriate crop parameters.
     */
    cropLast: function(data) {
      var workflow = this.props.workflow,
          shotPages = data.pages;
      if (data.retake) {
        // Don't crop on retakes
        return;
      }
      console.log("Cropping last capture");
      _.each(shotPages, function(page) {
        var pageNum = page.capture_num,
            // This is safe, since we don't crop on retakes
            toCrop = pageNum-2,
            targetPage = page.sequence_num%2 > 0 ? 'odd': 'even';
        this.props.workflow.cropPage({
          pageNum: toCrop,
          cropParams: this.state.cropParams[targetPage]
        });
      }, this);
    },

    /**
     * Toggle display of activity overlay.
     *
     * @param {string} message - Message to display on overlay
     */
    toggleWaiting: function(message) {
      if (!this.state.waiting) {
        this.setState({
          waiting: true,
          waitMessage: message || ''
        });
      } else {
        this.setState({waiting: false});
      }
    },

    bindCropEvents: function() {
      if (!this.state.cropOnSuccess) {
        this.props.workflow.on('capture-succeeded', this.cropLast, this);
        this.setState({cropOnSuccess: true})
      }
    },

    setCropParams: function(targetPage, params) {
      // Register event to crop the previous picture for any new picture taken
      // We don't send this manually with each capture trigger, since we also
      // want to catch captures triggered from the backend (i.e. via the
      // hidtrigger plugin)
      var origParams = this.state.cropParams,
          storageKey = 'crop-params.' + this.props.workflow.id,
          paramJson;
      this.bindCropEvents();
      origParams[targetPage] = params;
      paramJson = JSON.stringify(origParams);
      if (paramJson != localStorage.getItem(storageKey)) {
        localStorage.setItem(storageKey, paramJson);
      }
      this.setState({
        cropParams: origParams,
        cropTarget: undefined
      });
    },

    handleConfigUpdate: function() {
        this.toggleWaiting("Please wait until the devices are reconfigured.");
        this.props.workflow.prepareCapture({onSuccess: this.toggleWaiting,
                                            reset: true});
    },

    render: function() {
      var workflow = this.props.workflow || {},
          oddImage, evenImage, captureKeys, previewClasses;

      previewClasses = {
        'capture-preview': true,
        'small-block-grid-2': util.getOrientation() === 'landscape',
        'small-block-grid-1': util.getOrientation() === 'portrait',
        'medium-block-grid-2': util.getOrientation() === 'portrait'
      }

      captureKeys = [] ;
      _.each(window.config.core.capture_keys, function(key) {
        if (key === ' ') captureKeys.push('<spacebar>');
        else captureKeys.push(key);
      });

      if (workflow.get('pages').length) {
        var lastPages = _.sortBy(workflow.get('pages').slice(-2), 'capture_num');
        evenImage = util.getPageUrl(workflow, lastPages[0].capture_num, 'raw');
        oddImage = util.getPageUrl(workflow, lastPages[1].capture_num, 'raw');
      }

      return (
        <div>
          <F.Row>
            <F.Column>
                <ul className={React.addons.classSet(previewClasses)}>
                  <Preview targetPage="even" imageSrc={evenImage}
                    cropParams={this.state.cropParams['even']}
                    onCropParamUpdate={_.partial(this.setCropParams, 'even')}
                    showCropPreview={this.state.captureStart > 0} />
                  <Preview targetPage="odd" imageSrc={oddImage}
                    cropParams={this.state.cropParams['odd']}
                    onCropParamUpdate={_.partial(this.setCropParams, 'odd')}
                    showCropPreview={this.state.captureStart > 0}/>
              </ul>
            </F.Column>
          </F.Row>
          <StatusDisplay numPages={this.props.workflow.get('pages').length}
                         numExpected={this.props.workflow.get('metadata').extent | 0}
                         captureStart={this.state.captureStart} />
          <Control workflow={this.props.workflow}
                   onConfigUpdate={this.handleConfigUpdate}
                   onFinish={this.state.waiting ? function(){} : this.handleFinish} />
          <ShortcutHelp captureKeys={captureKeys} />
        </div>
      );
    },

    renderLayer: function() {
      if (this.state.waiting) return <LoadingOverlay message={this.state.waitMessage} />;
      else return null;
    }
  });

  module.exports = {
    CaptureScreen: CaptureScreen
  };
})();
