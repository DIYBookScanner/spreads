/** @jsx React.DOM */
/* global module, require, console */
(function() {
  'use strict';

  var React = require('react/addons'),
      foundation = require('./foundation.js'),
      ModelMixin = require('../../lib/backbonemixin.js'),
      LoadingOverlay = require('./overlays.js').Activity,
      lightbox = require('./overlays.js').LightBox,
      PluginWidget = require('./config.js').PluginWidget,
      row = foundation.row,
      column = foundation.column,
      fnButton = foundation.button,
      confirmModal = foundation.confirmModal;


  /**
   * Screen component to control the capture process.
   *
   * @property {Workflow} workflow - Workflow to control capture on
   */
  module.exports = React.createClass({
    displayName: "CaptureScreen",

    /** Enables two-way databinding with Backbone model */
    mixins: [ModelMixin],

    /** Activates databinding for `workflow` model property. */
    getBackboneModels: function() {
      return [this.props.workflow];
    },
    getInitialState: function() {
      return {
        /** Display activity overlay? */
        waiting: false,
        /** Initial number of pages shot */
        initialPageCount: this.props.workflow.get('images').length,
        /** Message for activity overlay */
        waitMessage: undefined,
        /** Time of first capture */
        captureStart: undefined,
        /** Validation errors for device configuration */
        validationErrors: {}
      };
    },
    /**
     * Triggers preparation of capture on workflow and displays the activity
     * overlay until the process is finished.
     */
    componentWillMount: function() {
      this.toggleWaiting("Please wait while the devices  are being prepared " +
                          "for capture");
      this.props.workflow.on('capture-triggered', function(){
        this.toggleWaiting("Please wait for the capture to finish...");
      }, this);
      this.props.workflow.on('capture-succeeded', this.toggleWaiting);
      this.props.workflow.prepareCapture(this.toggleWaiting);
    },
    /**
     * Triggers finish of capture on workflow.
     */
    componentWillUnmount: function() {
      console.log("Wrapping up capture process");
      this.props.workflow.finishCapture();
    },
    /**
     * Trigger a single capture, display activity overlay until it is finished
     */
    handleCapture: function() {
      console.log("Triggering capture");
      this.props.workflow.triggerCapture(false, function() {
        if (this.state.refreshReview) {
          this.setState({refreshReview: false});
        }
      }.bind(this));
    },
    /**
     * Trigger a retake (= delete last <num_devices> captures and take new
     * ones, display activity overlay until it is finished.
     */
    handleRetake: function() {
      console.log("Re-taking last shot");
      this.props.workflow.triggerCapture(true, function() {
        if (!this.state.refreshReview) {
          this.setState({refreshReview: true});
        }
      }.bind(this));
    },
    /**
     * Finish capture and navigate back to workflow list screen
     */
    handleFinish: function() {
      window.router.navigate('/', {trigger: true});
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
    toggleConfigModal: function() {
      this.setState({
        displayConfig: !this.state.displayConfig
      });
    },
    saveConfig: function() {
      this.props.workflow.on('validated:invalid', function(workflow, errors) {
        this.setState({validationErrors: errors});
      }, this);
      var xhr = this.props.workflow.save();
      if (xhr) {
        xhr.done(function() {
          this.toggleConfigModal();
          this.toggleWaiting("Configuring cameras.")
          this.props.workflow.prepareCapture(this.toggleWaiting, true);
          this.props.workflow.off('validated:invalid', null, this);
        }.bind(this))
      };
    },
    /**
     * Open image in lightbox overlay
     *
     * @param {url} - Image to display in lightbox
     */
    openLightbox: function(img) {
      this.setState({
        lightboxImage: img
      });
    },
    /**
     * Close the lightbox overlay.
     */
    closeLightbox: function() {
      this.setState({
        lightboxImage: undefined,
        refreshReview: false,
      });
    },
    render: function() {
      var workflow = this.props.workflow || {},
          randomSuffix = this.state.refreshReview ? '?'+(Math.random()*10e3 | 0) : '',
          speed, oddImage, evenImage;
      if (workflow && this.state.captureStart) {
        var elapsed = (new Date().getTime()/1000) - this.state.captureStart,
            shot = workflow.get('images').length - this.state.initialPageCount;
        speed = (3600/elapsed)*shot | 0;
      } else {
        this.setState({captureStart: new Date().getTime()/1000});
        speed = 0.0;
      }
      if (workflow.get('images').length) {
        oddImage = workflow.get('images').slice(-2)[0];
        evenImage = workflow.get('images').slice(-2)[1];
      }

      return (
        <div>
          {/* Display loading overlay? */}
          {this.state.waiting && <LoadingOverlay message={this.state.waitMessage} />}
          {/* Display lightbox overlay? */}
          {this.state.lightboxImage &&
            <lightbox onClose={this.closeLightbox} src={this.state.lightboxImage} />}
          {this.state.displayConfig &&
            <form onSubmit={this.saveConfig}>
              <confirmModal onCancel={this.toggleConfigModal}>
                <PluginWidget plugin="device" template={window.pluginTemplates.device}
                              bindFunc={function(key) {
                                return this.bindTo(this.props.workflow,
                                                    'config.device.' + key);
                              }.bind(this)} errors={[]}/>
              </confirmModal>
            </form>
          }
          {/* Only display review images if there are images on the workflow */}
          {(oddImage && evenImage) &&
          <row>
            <column>
              {/* NOTE: We append a random suffix to the thumbnail URL to force
                *       the browser to load from the server and not from the cache.
                *       This is needed since the images might change on the server,
                *       e.g. after a retake. */}
              {/* Landscape layout */}
              <ul className="show-for-landscape small-block-grid-2 capture-preview">
                <li>
                  <a title="Open full resolution image in lightbox" onClick={function(){this.openLightbox(oddImage+'?'+randomSuffix);}.bind(this)}>
                    <img src={oddImage+"/thumb?"+randomSuffix} />
                  </a>
                </li>
                <li>
                  <a title="Open full resolution image in lightbox" onClick={function(){this.openLightbox(evenImage+'?'+randomSuffix);}.bind(this)}>
                    <img src={evenImage+"/thumb?"+randomSuffix} />
                  </a>
                </li>
              </ul>
              {/* Portrait layout */}
              <ul className="show-for-portrait small-block-grid-1 medium-block-grid-2 capture-preview">
                  <li>
                    <a title="Open full resolution image in lightbox" onClick={function(){this.openLightbox(oddImage+'?'+randomSuffix);}.bind(this)}>
                      <img src={oddImage+"/thumb?"+randomSuffix} />
                    </a>
                  </li>
                <li>
                  <a title="Open full resolution image in lightbox" onClick={function(){this.openLightbox(evenImage+'?'+randomSuffix);}.bind(this)}>
                    <img src={evenImage+"/thumb?"+randomSuffix} />
                  </a>
                </li>
              </ul>
            </column>
          </row>}
          <row className="capture-info">
            <column size="6">
              <span className="pagecount">{workflow.get('images').length} pages</span>
            </column>
            {speed > 0 &&
            <column size="6">
              <span className="capturespeed">{speed} pages/hour</span>
            </column>}
          </row>
          <row>
            <div className="small-12 capture-controls columns">
              <ul>
                <li id="retake-capture">
                  <fnButton title="Discard last capture and take a new one"
                            callback={this.handleRetake} secondary='true'>
                      <i className="fi-refresh"></i>
                  </fnButton>
                </li>
                <li id="trigger-capture">
                  <fnButton title="Trigger capture"
                            callback={this.handleCapture}>
                    <i className="fi-camera"></i>
                  </fnButton>
                </li>
                <li>
                  <fnButton title="Configure devices"
                            callback={this.toggleConfigModal} secondary='true'>
                    <i className="fi-widget"></i>
                  </fnButton>
                </li>
                <li>
                  <fnButton title="Finish capture and return to workflow list"
                            callback={this.handleFinish} complete={true}>
                    <i className="fi-check"></i>
                  </fnButton>
                </li>
              </ul>
            </div>
          </row>
          <row>
            <column size="1" offset="5">
            </column>
          </row>
        </div>
      );
    }
  });
})();
